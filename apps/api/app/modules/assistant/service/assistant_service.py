from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.schemas import HookConfig, ModelConfig
from app.modules.credential.service import CredentialService
from app.modules.credential.service.credential_connection_support import build_runtime_credential_payload
from app.modules.project.service import ProjectService
from app.shared.runtime import PluginRegistry, SkillTemplateRenderer, ToolProvider
from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm_tool_provider import LLM_GENERATE_TOOL, LLMStreamEvent
from app.shared.runtime.provider_interop_stream_support import StreamInterruptedError

from .assistant_rule_service import AssistantRuleService
from .assistant_rule_support import build_assistant_system_prompt
from .assistant_agent_service import AssistantAgentService
from .assistant_hook_service import AssistantHookService
from .assistant_mcp_service import AssistantMcpService
from .assistant_skill_service import AssistantSkillService
from .assistant_tool_executor import AssistantToolExecutor
from .assistant_tool_exposure_policy import AssistantToolExposurePolicy
from .assistant_tool_loop import AssistantToolLoop
from .assistant_tool_registry import AssistantToolDescriptorRegistry
from .assistant_hook_providers import build_assistant_plugin_registry
from .assistant_hook_support import (
    AssistantHookExecutionContext,
    matches_hook_condition,
    normalize_hook_result,
    resolve_assistant_hooks_for_event,
    serialize_hook_error,
)
from .assistant_execution_support import (
    AssistantExecutionSpec,
    build_hook_agent_variables,
    hook_agent_response_format,
    render_prompt,
    require_agent_skill,
    require_text_output,
    resolve_execution_spec,
    resolve_hook_agent_output,
    resolve_hook_agent_model,
    validate_retry_policy,
)
from .assistant_turn_runtime_support import (
    PreparedAssistantTurn,
    build_after_assistant_payload,
    build_before_assistant_payload,
    build_turn_context,
    build_turn_response,
)
from .dto import AssistantHookResultDTO, AssistantTurnRequestDTO, AssistantTurnResponseDTO
from .preferences_service import AssistantPreferencesService


@dataclass(frozen=True)
class AssistantStreamEvent:
    event: str
    data: dict[str, Any]


class AssistantService:
    def __init__(
        self,
        *,
        assistant_rule_service: AssistantRuleService,
        assistant_agent_service: AssistantAgentService | None = None,
        assistant_hook_service: AssistantHookService | None = None,
        assistant_mcp_service: AssistantMcpService | None = None,
        assistant_preferences_service: AssistantPreferencesService | None = None,
        assistant_skill_service: AssistantSkillService | None = None,
        config_loader: ConfigLoader,
        credential_service_factory: Callable[[], CredentialService],
        project_service: ProjectService,
        tool_provider: ToolProvider,
        template_renderer: SkillTemplateRenderer,
        plugin_registry: PluginRegistry | None = None,
        assistant_tool_descriptor_registry: AssistantToolDescriptorRegistry | None = None,
        assistant_tool_exposure_policy: AssistantToolExposurePolicy | None = None,
        assistant_tool_executor: AssistantToolExecutor | None = None,
        assistant_tool_loop: AssistantToolLoop | None = None,
    ) -> None:
        self.assistant_rule_service = assistant_rule_service
        self.config_loader = config_loader
        self.project_service = project_service
        self.assistant_preferences_service = assistant_preferences_service or AssistantPreferencesService(
            project_service=project_service
        )
        self.assistant_skill_service = assistant_skill_service or AssistantSkillService(
            config_loader=config_loader,
            project_service=project_service,
        )
        self.assistant_agent_service = assistant_agent_service or AssistantAgentService(
            assistant_skill_service=self.assistant_skill_service,
            config_loader=config_loader,
        )
        self.assistant_mcp_service = assistant_mcp_service or AssistantMcpService(
            config_loader=config_loader,
            project_service=project_service,
        )
        self.assistant_hook_service = assistant_hook_service or AssistantHookService(
            assistant_agent_service=self.assistant_agent_service,
            assistant_mcp_service=self.assistant_mcp_service,
            config_loader=config_loader,
        )
        self.credential_service_factory = credential_service_factory
        self.tool_provider = tool_provider
        self.template_renderer = template_renderer
        self.assistant_tool_descriptor_registry = assistant_tool_descriptor_registry
        self.assistant_tool_exposure_policy = assistant_tool_exposure_policy
        self.assistant_tool_executor = assistant_tool_executor
        self.assistant_tool_loop = assistant_tool_loop
        self.plugin_registry = plugin_registry or build_assistant_plugin_registry(
            self,
            mcp_server_resolver=lambda context, server_id: self.assistant_mcp_service.resolve_mcp_server(
                server_id,
                owner_id=context.owner_id,
                project_id=context.project_id,
            ),
        )
        self._credential_service: CredentialService | None = None

    async def turn(
        self,
        db: AsyncSession,
        payload: AssistantTurnRequestDTO,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantTurnResponseDTO:
        prepared = await self._prepare_turn(db, payload, owner_id=owner_id)
        before_results = await self._run_before_turn_hooks(db, prepared, owner_id=owner_id)
        raw_output = await self._call_turn_llm(
            db,
            prepared.hooks,
            prompt=prepared.prompt,
            before_payload=prepared.before_payload,
            owner_id=owner_id,
            project_id=prepared.project_id,
            spec=prepared.spec,
            system_prompt=prepared.system_prompt,
            turn_context=prepared.turn_context,
        )
        return await self._finalize_turn(
            db,
            payload,
            prepared,
            raw_output,
            before_results=before_results,
            owner_id=owner_id,
        )

    async def stream_turn(
        self,
        db: AsyncSession,
        payload: AssistantTurnRequestDTO,
        *,
        owner_id: uuid.UUID,
        should_stop: Callable[[], Awaitable[bool]] | None = None,
    ) -> AsyncIterator[AssistantStreamEvent]:
        prepared = await self._prepare_turn(db, payload, owner_id=owner_id)
        before_results = await self._run_before_turn_hooks(db, prepared, owner_id=owner_id)
        raw_output: dict[str, Any] | None = None
        event_seq = 1
        yield AssistantStreamEvent(
            "run_started",
            self._build_stream_event_data(
                prepared,
                event_seq=event_seq,
                state_version=1,
                extra={
                    "requested_write_scope": prepared.turn_context.requested_write_scope,
                    "requested_write_targets": prepared.turn_context.requested_write_targets,
                },
            ),
        )
        if self._should_use_tool_loop_stream(prepared):
            async for event_name, event_data in self._stream_turn_with_tool_loop(
                db,
                prepared,
                owner_id=owner_id,
                should_stop=should_stop,
            ):
                if event_name == "final_output":
                    raw_output = event_data
                    continue
                event_seq += 1
                yield AssistantStreamEvent(
                    event_name,
                    self._build_stream_event_data(
                        prepared,
                        event_seq=event_seq,
                        state_version=1,
                        extra=event_data,
                    ),
                )
        else:
            async for event in self._call_turn_llm_stream(
                db,
                prepared.hooks,
                prompt=prepared.prompt,
                before_payload=prepared.before_payload,
                owner_id=owner_id,
                project_id=prepared.project_id,
                spec=prepared.spec,
                system_prompt=prepared.system_prompt,
                should_stop=should_stop,
            ):
                if event.delta:
                    event_seq += 1
                    yield AssistantStreamEvent(
                        "chunk",
                        self._build_stream_event_data(
                            prepared,
                            event_seq=event_seq,
                            state_version=1,
                            extra={"delta": event.delta},
                        ),
                    )
                    continue
                raw_output = event.response
        if raw_output is None:
            raise ConfigurationError("Streaming response completed without final output")
        response = await self._finalize_turn(
            db,
            payload,
            prepared,
            raw_output,
            before_results=before_results,
            owner_id=owner_id,
        )
        event_seq += 1
        completed_payload = response.model_dump(mode="json")
        completed_payload.update(
            self._build_stream_event_data(
                prepared,
                event_seq=event_seq,
                state_version=2,
            )
        )
        yield AssistantStreamEvent(
            "completed",
            completed_payload,
        )

    async def run_agent_hook(
        self,
        context: AssistantHookExecutionContext,
        *,
        agent_id: str,
        input_mapping: dict[str, str],
    ) -> Any:
        agent = self.assistant_agent_service.resolve_agent(
            agent_id,
            owner_id=context.owner_id,
            allow_disabled=True,
        )
        skill = require_agent_skill(
            lambda skill_id: self.assistant_skill_service.resolve_skill(
                skill_id,
                owner_id=context.owner_id,
                project_id=context.project_id,
                allow_disabled=True,
            ),
            agent,
        )
        variables = build_hook_agent_variables(context, input_mapping)
        prompt = self.template_renderer.render(skill.prompt, variables)
        preferences = await self.assistant_preferences_service.resolve_preferences(
            context.db,
            owner_id=context.owner_id,
            project_id=context.project_id,
        )
        model = resolve_hook_agent_model(
            agent=agent,
            skill=skill,
            preferences=preferences,
            assistant_model=context.assistant_model,
        )
        rule_bundle = await self.assistant_rule_service.build_rule_bundle(
            context.db,
            owner_id=context.owner_id,
            project_id=context.project_id,
        )
        system_prompt = build_assistant_system_prompt(
            agent.system_prompt,
            user_content=rule_bundle.user_content,
            project_content=rule_bundle.project_content,
        )
        raw_output = await self._call_llm(
            context.db,
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            owner_id=context.owner_id,
            project_id=context.project_id,
            response_format=hook_agent_response_format(agent),
        )
        return resolve_hook_agent_output(agent, raw_output.get("content"))

    async def _prepare_turn(
        self,
        db: AsyncSession,
        payload: AssistantTurnRequestDTO,
        *,
        owner_id: uuid.UUID,
    ) -> PreparedAssistantTurn:
        project_id = await self._resolve_project_scope(db, payload.project_id, owner_id=owner_id)
        preferences = await self.assistant_preferences_service.resolve_preferences(
            db,
            owner_id=owner_id,
            project_id=project_id,
        )
        spec = resolve_execution_spec(
            self.config_loader,
            payload,
            preferences,
            load_agent=lambda agent_id: self.assistant_agent_service.resolve_agent(
                agent_id,
                owner_id=owner_id,
            ),
            load_skill=lambda skill_id: self.assistant_skill_service.resolve_skill(
                skill_id,
                owner_id=owner_id,
                project_id=project_id,
                allow_disabled=payload.agent_id is not None,
            ),
        )
        rule_bundle = await self.assistant_rule_service.build_rule_bundle(
            db,
            owner_id=owner_id,
            project_id=project_id,
        )
        turn_context = build_turn_context(
            spec,
            payload,
            owner_id=owner_id,
            project_id=project_id,
            user_rule_content=rule_bundle.user_content,
            project_rule_content=rule_bundle.project_content,
        )
        return PreparedAssistantTurn(
            before_payload=build_before_assistant_payload(spec, payload, project_id, turn_context),
            hooks=[
                self.assistant_hook_service.resolve_hook(hook_id, owner_id=owner_id)
                for hook_id in payload.hook_ids
            ],
            project_id=project_id,
            prompt=render_prompt(
                template_renderer=self.template_renderer,
                skill=spec.skill,
                payload=payload,
            ),
            spec=spec,
            system_prompt=build_assistant_system_prompt(
                spec.system_prompt,
                user_content=rule_bundle.user_content,
                project_content=rule_bundle.project_content,
            ),
            turn_context=turn_context,
        )

    async def _run_before_turn_hooks(
        self,
        db: AsyncSession,
        prepared: PreparedAssistantTurn,
        *,
        owner_id: uuid.UUID,
    ) -> list[AssistantHookResultDTO]:
        return await self._run_hook_event(
            db,
            prepared.hooks,
            "before_assistant_response",
            payload=prepared.before_payload,
            owner_id=owner_id,
            project_id=prepared.project_id,
            agent_id=prepared.spec.agent_id,
            skill_id=prepared.spec.skill_id,
            assistant_model=prepared.spec.model,
        )

    async def _finalize_turn(
        self,
        db: AsyncSession,
        payload: AssistantTurnRequestDTO,
        prepared: PreparedAssistantTurn,
        raw_output: dict[str, Any],
        *,
        before_results: list[AssistantHookResultDTO],
        owner_id: uuid.UUID,
    ) -> AssistantTurnResponseDTO:
        content = require_text_output(raw_output.get("content"))
        after_payload = build_after_assistant_payload(
            prepared.spec,
            payload,
            prepared.project_id,
            prepared.turn_context,
            content,
        )
        after_results = await self._run_hook_event(
            db,
            prepared.hooks,
            "after_assistant_response",
            payload=after_payload,
            owner_id=owner_id,
            project_id=prepared.project_id,
            agent_id=prepared.spec.agent_id,
            skill_id=prepared.spec.skill_id,
            assistant_model=prepared.spec.model,
        )
        return build_turn_response(
            prepared.spec,
            raw_output,
            content,
            before_results + after_results,
            prepared.turn_context,
        )

    async def _resolve_project_scope(
        self,
        db: AsyncSession,
        project_id: uuid.UUID | None,
        *,
        owner_id: uuid.UUID,
    ) -> uuid.UUID | None:
        if project_id is None:
            return None
        return (await self.project_service.require_project(db, project_id, owner_id=owner_id)).id

    def _build_stream_event_data(
        self,
        prepared: PreparedAssistantTurn,
        *,
        event_seq: int,
        state_version: int,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "run_id": str(prepared.turn_context.run_id),
            "conversation_id": prepared.turn_context.conversation_id,
            "client_turn_id": prepared.turn_context.client_turn_id,
            "event_seq": event_seq,
            "state_version": state_version,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        if extra:
            payload.update(extra)
        return payload

    async def _run_hook_event(
        self,
        db: AsyncSession,
        hooks: list[HookConfig],
        event: str,
        *,
        payload: dict[str, Any],
        owner_id: uuid.UUID,
        project_id: uuid.UUID | None,
        agent_id: str | None,
        skill_id: str | None,
        assistant_model: ModelConfig,
    ) -> list[AssistantHookResultDTO]:
        context = AssistantHookExecutionContext(
            db=db,
            event=event,
            owner_id=owner_id,
            payload=payload,
            assistant_agent_id=agent_id,
            assistant_skill_id=skill_id,
            assistant_model=assistant_model,
            project_id=project_id,
        )
        results: list[AssistantHookResultDTO] = []
        for hook in resolve_assistant_hooks_for_event(hooks, event):
            if not matches_hook_condition(hook, payload):
                continue
            result = await self._execute_hook_with_retry(context, hook)
            results.append(
                AssistantHookResultDTO(
                    event=event,
                    hook_id=hook.id,
                    action_type=hook.action.action_type,
                    result=normalize_hook_result(result),
                )
            )
        return results

    async def _execute_hook_with_retry(
        self,
        context: AssistantHookExecutionContext,
        hook: HookConfig,
    ) -> Any:
        attempts = hook.retry.max_attempts if hook.retry is not None else 1
        delay = hook.retry.delay if hook.retry is not None else 0
        validate_retry_policy(attempts, delay)
        for attempt in range(1, attempts + 1):
            try:
                return await self.plugin_registry.execute(
                    hook.action.action_type,
                    config=hook.action.config,
                    context=context,
                    timeout_seconds=hook.timeout,
                )
            except Exception:
                if attempt >= attempts:
                    raise
                await asyncio.sleep(delay)
        raise RuntimeError("Hook retry loop exited unexpectedly")

    async def _run_on_error_hooks(
        self,
        db: AsyncSession,
        hooks: list[HookConfig],
        payload: dict[str, Any],
        error: Exception,
        *,
        owner_id: uuid.UUID,
        project_id: uuid.UUID | None,
        agent_id: str | None,
        skill_id: str | None,
        assistant_model: ModelConfig,
    ) -> None:
        error_payload = dict(payload)
        error_payload["error"] = serialize_hook_error(error)
        try:
            await self._run_hook_event(
                db,
                hooks,
                "on_error",
                payload=error_payload,
                owner_id=owner_id,
                project_id=project_id,
                agent_id=agent_id,
                skill_id=skill_id,
                assistant_model=assistant_model,
            )
        except Exception as hook_exc:
            raise ExceptionGroup("Assistant runtime error and on_error hook both failed", [error, hook_exc]) from hook_exc

    async def _call_turn_llm(
        self,
        db: AsyncSession,
        hooks: list[HookConfig],
        *,
        prompt: str,
        before_payload: dict[str, Any],
        owner_id: uuid.UUID,
        project_id: uuid.UUID | None,
        spec: AssistantExecutionSpec,
        system_prompt: str | None,
        turn_context,
    ) -> dict[str, Any]:
        try:
            if self.assistant_tool_loop is not None:
                loop_result = await self.assistant_tool_loop.execute(
                    db,
                    turn_context=turn_context,
                    owner_id=owner_id,
                    project_id=project_id,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model_caller=lambda *, prompt, system_prompt, tools: self._call_llm(
                        db,
                        prompt=prompt,
                        system_prompt=system_prompt,
                        model=spec.model,
                        owner_id=owner_id,
                        project_id=project_id,
                        tools=tools,
                    ),
                )
                return loop_result.raw_output
            return await self._call_llm(
                db,
                prompt=prompt,
                system_prompt=system_prompt,
                model=spec.model,
                owner_id=owner_id,
                project_id=project_id,
            )
        except Exception as exc:
            await self._run_on_error_hooks(
                db,
                hooks,
                before_payload,
                exc,
                owner_id=owner_id,
                project_id=project_id,
                agent_id=spec.agent_id,
                skill_id=spec.skill_id,
                assistant_model=spec.model,
            )
            raise

    async def _call_turn_llm_stream(
        self,
        db: AsyncSession,
        hooks: list[HookConfig],
        *,
        prompt: str,
        before_payload: dict[str, Any],
        owner_id: uuid.UUID,
        project_id: uuid.UUID | None,
        spec: AssistantExecutionSpec,
        system_prompt: str | None,
        tools: list[dict[str, Any]] | None = None,
        should_stop: Callable[[], Awaitable[bool]] | None = None,
    ) -> AsyncIterator[LLMStreamEvent]:
        try:
            async for event in self._call_llm_stream(
                db,
                prompt=prompt,
                system_prompt=system_prompt,
                model=spec.model,
                owner_id=owner_id,
                project_id=project_id,
                tools=tools,
                should_stop=should_stop,
            ):
                yield event
        except StreamInterruptedError:
            raise
        except Exception as exc:
            await self._run_on_error_hooks(
                db,
                hooks,
                before_payload,
                exc,
                owner_id=owner_id,
                project_id=project_id,
                agent_id=spec.agent_id,
                skill_id=spec.skill_id,
                assistant_model=spec.model,
            )
            raise

    async def _stream_turn_with_tool_loop(
        self,
        db: AsyncSession,
        prepared: PreparedAssistantTurn,
        *,
        owner_id: uuid.UUID,
        should_stop: Callable[[], Awaitable[bool]] | None = None,
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        if self.assistant_tool_loop is None:
            raise ConfigurationError("Assistant tool loop is not configured")
        tool_schemas = self.assistant_tool_loop.resolve_tool_schemas(
            turn_context=prepared.turn_context,
            project_id=prepared.project_id,
        )
        if not tool_schemas:
            raise ConfigurationError("Assistant tool loop streaming requires visible tools")
        try:
            raw_output: dict[str, Any] | None = None
            async for event in self._call_llm_stream(
                db,
                prompt=prepared.prompt,
                system_prompt=prepared.system_prompt,
                model=prepared.spec.model,
                owner_id=owner_id,
                project_id=prepared.project_id,
                tools=tool_schemas,
                should_stop=should_stop,
            ):
                if event.delta:
                    yield "chunk", {"delta": event.delta}
                    continue
                raw_output = event.response
            if raw_output is None:
                raise ConfigurationError("Streaming response completed without initial output")
            if not self._has_tool_calls(raw_output):
                yield "final_output", raw_output
                return
            async for item in self.assistant_tool_loop.iterate(
                db,
                turn_context=prepared.turn_context,
                owner_id=owner_id,
                project_id=prepared.project_id,
                prompt=prepared.prompt,
                system_prompt=prepared.system_prompt,
                model_caller=lambda *, prompt, system_prompt, tools: self._call_llm(
                    db,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model=prepared.spec.model,
                    owner_id=owner_id,
                    project_id=prepared.project_id,
                    tools=tools,
                ),
                initial_raw_output=raw_output,
                should_stop=should_stop,
            ):
                if item.event_name is not None and item.event_payload is not None:
                    yield item.event_name, item.event_payload
                    continue
                if item.raw_output is None:
                    continue
                buffered_chunk = self._build_buffered_final_chunk_payload(item.raw_output)
                if buffered_chunk is not None:
                    yield "chunk", buffered_chunk
                yield "final_output", item.raw_output
        except StreamInterruptedError:
            raise
        except Exception as exc:
            await self._run_on_error_hooks(
                db,
                prepared.hooks,
                prepared.before_payload,
                exc,
                owner_id=owner_id,
                project_id=prepared.project_id,
                agent_id=prepared.spec.agent_id,
                skill_id=prepared.spec.skill_id,
                assistant_model=prepared.spec.model,
            )
            raise

    def _should_use_tool_loop_stream(self, prepared: PreparedAssistantTurn) -> bool:
        if self.assistant_tool_loop is None:
            return False
        return bool(
            self.assistant_tool_loop.resolve_tool_schemas(
                turn_context=prepared.turn_context,
                project_id=prepared.project_id,
            )
        )

    def _has_tool_calls(self, raw_output: dict[str, Any]) -> bool:
        tool_calls = raw_output.get("tool_calls")
        return isinstance(tool_calls, list) and bool(tool_calls)

    def _build_buffered_final_chunk_payload(
        self,
        raw_output: dict[str, Any],
    ) -> dict[str, Any] | None:
        content = raw_output.get("content")
        if not isinstance(content, str) or not content:
            return None
        return {"delta": content, "chunk_kind": "buffered_final"}

    async def _call_llm(
        self,
        db: AsyncSession,
        *,
        prompt: str,
        system_prompt: str | None,
        model: ModelConfig,
        owner_id: uuid.UUID,
        project_id: uuid.UUID | None,
        response_format: str = "text",
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        credential_service = self._resolve_credential_service()
        credential = await credential_service.resolve_active_credential(
            db,
            provider=model.provider or "",
            user_id=owner_id,
            project_id=project_id,
        )
        return await self.tool_provider.execute(
            LLM_GENERATE_TOOL,
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "model": model.model_dump(mode="json", exclude_none=True),
                "credential": build_runtime_credential_payload(
                    credential,
                    decrypt_api_key=credential_service.crypto.decrypt,
                ),
                "response_format": response_format,
                "tools": list(tools or []),
            },
        )

    async def _call_llm_stream(
        self,
        db: AsyncSession,
        *,
        prompt: str,
        system_prompt: str | None,
        model: ModelConfig,
        owner_id: uuid.UUID,
        project_id: uuid.UUID | None,
        tools: list[dict[str, Any]] | None = None,
        should_stop: Callable[[], Awaitable[bool]] | None = None,
    ) -> AsyncIterator[LLMStreamEvent]:
        credential_service = self._resolve_credential_service()
        credential = await credential_service.resolve_active_credential(
            db,
            provider=model.provider or "",
            user_id=owner_id,
            project_id=project_id,
        )
        stream_executor = getattr(self.tool_provider, "execute_stream", None)
        if not callable(stream_executor):
            raise ConfigurationError("Current assistant runtime does not support streaming")
        async for event in stream_executor(
            LLM_GENERATE_TOOL,
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "model": model.model_dump(mode="json", exclude_none=True),
                "credential": build_runtime_credential_payload(
                    credential,
                    decrypt_api_key=credential_service.crypto.decrypt,
                ),
                "response_format": "text",
                "tools": list(tools or []),
            },
            should_stop=should_stop,
        ):
            yield event

    def _resolve_credential_service(self) -> CredentialService:
        if self._credential_service is None:
            self._credential_service = self.credential_service_factory()
        return self._credential_service
