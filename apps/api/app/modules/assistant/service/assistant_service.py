from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.schemas import HookConfig, ModelConfig
from app.modules.credential.service import CredentialService
from app.modules.project.service import (
    ProjectDocumentCapabilityService,
    ProjectService,
)
from app.shared.runtime import PluginRegistry, SkillTemplateRenderer, ToolProvider
from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.llm_tool_provider import LLMStreamEvent

from .rules.assistant_rule_service import AssistantRuleService
from .agents.assistant_agent_service import AssistantAgentService
from .hooks.assistant_hook_service import AssistantHookService
from .mcp.assistant_mcp_service import AssistantMcpService
from .skills.assistant_skill_service import AssistantSkillService
from .tooling.assistant_tool_executor import AssistantToolExecutor
from .tooling.assistant_tool_exposure_policy import AssistantToolExposurePolicy
from .tooling.assistant_tool_loop import AssistantToolLoop
from .tooling.assistant_tool_registry import AssistantToolDescriptorRegistry
from .hooks_runtime.assistant_hook_providers import build_assistant_plugin_registry
from .hooks_runtime.assistant_hook_support import (
    AssistantHookExecutionContext,
)
from .hooks_runtime.assistant_hook_runtime_support import (
    execute_assistant_hook_with_retry,
    run_assistant_agent_hook,
    run_assistant_hook_event,
    run_assistant_on_error_hooks,
    run_before_turn_hooks,
    run_prepare_on_error_hooks,
    run_prepared_on_error_hooks,
)
from .assistant_execution_support import (
    AssistantExecutionSpec,
    require_text_output,
)
from .assistant_runtime_terminal import (
    AssistantRuntimeTerminalError,
    attach_assistant_stream_error_meta,
)
from .assistant_runtime_claim_support import (
    build_current_runtime_claim_snapshot,
    resolve_runtime_claim_state,
)
from .turn.assistant_turn_runtime_support import (
    PreparedAssistantTurn,
    build_after_assistant_payload,
    build_turn_response,
)
from .turn.assistant_turn_prepare_support import prepare_assistant_turn, resolve_requested_hooks
from .turn.assistant_turn_llm_bridge_support import (
    call_assistant_turn_llm,
    should_stream_with_tool_loop,
    stream_assistant_turn_llm,
    stream_assistant_turn_with_tool_loop,
)
from .assistant_llm_runtime_support import (
    ResolvedAssistantLlmRuntime,
    call_assistant_llm,
    resolve_assistant_llm_runtime,
    stream_assistant_llm,
)
from .turn.assistant_turn_run_store import AssistantTurnRunStore
from .turn.assistant_turn_run_support import (
    build_running_turn_record,
    build_terminal_turn_record,
    ensure_existing_turn_matches_request,
    recover_existing_turn,
)
from .dto import (
    AssistantHookResultDTO,
    AssistantTurnRequestDTO,
    AssistantTurnResponseDTO,
)
from .preferences.preferences_service import AssistantPreferencesService


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
        turn_run_store: AssistantTurnRunStore | None = None,
        project_document_capability_service: ProjectDocumentCapabilityService | None = None,
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
        self.turn_run_store = turn_run_store
        self.project_document_capability_service = (
            project_document_capability_service
            or (
                assistant_tool_executor.project_document_capability_service
                if assistant_tool_executor is not None
                else None
            )
        )
        self.plugin_registry = plugin_registry or build_assistant_plugin_registry(
            self,
            mcp_server_resolver=lambda context, server_id: self.assistant_mcp_service.resolve_mcp_server(
                server_id,
                owner_id=context.owner_id,
                project_id=context.project_id,
            ),
        )
        self._credential_service: CredentialService | None = None
        self.runtime_claim_snapshot = build_current_runtime_claim_snapshot()

    async def turn(
        self,
        db: AsyncSession,
        payload: AssistantTurnRequestDTO,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantTurnResponseDTO:
        resolved_hooks: list[HookConfig] = []
        try:
            resolved_hooks = resolve_requested_hooks(
                assistant_hook_service=self.assistant_hook_service,
                hook_ids=payload.hook_ids,
                owner_id=owner_id,
            )
            prepared = await self._prepare_turn(
                db,
                payload,
                owner_id=owner_id,
                resolved_hooks=resolved_hooks,
            )
        except Exception as exc:
            hook_error = await self._run_prepare_on_error_hooks(
                db,
                payload,
                hooks=resolved_hooks,
                error=exc,
                owner_id=owner_id,
            )
            if hook_error is not None:
                raise hook_error
            raise
        replayed_response = self._recover_or_start_turn(prepared, owner_id=owner_id)
        if replayed_response is not None:
            return replayed_response
        try:
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
                run_budget=prepared.run_budget,
                tool_policy_decisions=prepared.tool_policy_decisions,
                visible_tool_descriptors=prepared.visible_tool_descriptors,
                runtime_context=prepared.resolved_llm_runtime,
            )
            response = await self._finalize_turn(
                db,
                payload,
                prepared,
                raw_output,
                before_results=before_results,
                owner_id=owner_id,
            )
        except Exception as exc:
            hook_error = await self._run_prepared_on_error_hooks(
                db,
                prepared,
                error=exc,
                owner_id=owner_id,
            )
            self._store_terminal_turn(
                prepared,
                owner_id=owner_id,
                error=hook_error or exc,
            )
            if hook_error is not None:
                raise hook_error
            raise
        self._store_terminal_turn(
            prepared,
            owner_id=owner_id,
            response=response,
        )
        return response

    async def stream_turn(
        self,
        db: AsyncSession,
        payload: AssistantTurnRequestDTO,
        *,
        owner_id: uuid.UUID,
        should_stop: Callable[[], Awaitable[bool]] | None = None,
    ) -> AsyncIterator[AssistantStreamEvent]:
        resolved_hooks: list[HookConfig] = []
        try:
            resolved_hooks = resolve_requested_hooks(
                assistant_hook_service=self.assistant_hook_service,
                hook_ids=payload.hook_ids,
                owner_id=owner_id,
            )
            prepared = await self._prepare_turn(
                db,
                payload,
                owner_id=owner_id,
                resolved_hooks=resolved_hooks,
            )
        except Exception as exc:
            hook_error = await self._run_prepare_on_error_hooks(
                db,
                payload,
                hooks=resolved_hooks,
                error=exc,
                owner_id=owner_id,
            )
            if hook_error is not None:
                raise hook_error
            raise
        replayed_response = self._recover_or_start_turn(prepared, owner_id=owner_id)
        if replayed_response is not None:
            event_seq = 1
            yield AssistantStreamEvent(
                "run_started",
                self._build_stream_event_data(
                    prepared,
                    event_seq=event_seq,
                    extra={
                        "requested_write_scope": prepared.turn_context.requested_write_scope,
                        "requested_write_targets": prepared.turn_context.requested_write_targets,
                    },
                ),
            )
            event_seq += 1
            completed_payload = replayed_response.model_dump(mode="json")
            completed_payload.update(
                self._build_stream_event_data(
                    prepared,
                    event_seq=event_seq,
                )
            )
            yield AssistantStreamEvent("completed", completed_payload)
            return
        event_seq = 0
        try:
            before_results = await self._run_before_turn_hooks(db, prepared, owner_id=owner_id)
            raw_output: dict[str, Any] | None = None
            event_seq = 1
            yield AssistantStreamEvent(
                "run_started",
                self._build_stream_event_data(
                    prepared,
                    event_seq=event_seq,
                    extra={
                        "requested_write_scope": prepared.turn_context.requested_write_scope,
                        "requested_write_targets": prepared.turn_context.requested_write_targets,
                    },
                ),
            )
            if should_stream_with_tool_loop(
                assistant_tool_loop=self.assistant_tool_loop,
                prepared=prepared,
            ):
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
                    runtime_context=prepared.resolved_llm_runtime,
                    should_stop=should_stop,
                ):
                    if event.delta:
                        event_seq += 1
                        yield AssistantStreamEvent(
                            "chunk",
                            self._build_stream_event_data(
                                prepared,
                                event_seq=event_seq,
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
            self._store_terminal_turn(
                prepared,
                owner_id=owner_id,
                response=response,
            )
            event_seq += 1
            completed_payload = response.model_dump(mode="json")
            completed_payload.update(
                self._build_stream_event_data(
                    prepared,
                    event_seq=event_seq,
                )
            )
            yield AssistantStreamEvent(
                "completed",
                completed_payload,
            )
        except Exception as exc:
            hook_error = await self._run_prepared_on_error_hooks(
                db,
                prepared,
                error=exc,
                owner_id=owner_id,
            )
            self._store_terminal_turn(
                prepared,
                owner_id=owner_id,
                error=hook_error or exc,
            )
            stream_error = hook_error or exc
            attach_assistant_stream_error_meta(
                stream_error,
                self._build_stream_event_data(
                    prepared,
                    event_seq=event_seq + 1,
                ),
            )
            if hook_error is not None:
                raise hook_error
            raise

    async def run_agent_hook(
        self,
        context: AssistantHookExecutionContext,
        *,
        agent_id: str,
        input_mapping: dict[str, str],
    ) -> Any:
        return await run_assistant_agent_hook(
            context,
            agent_id=agent_id,
            input_mapping=input_mapping,
            assistant_agent_service=self.assistant_agent_service,
            assistant_skill_service=self.assistant_skill_service,
            assistant_preferences_service=self.assistant_preferences_service,
            assistant_rule_service=self.assistant_rule_service,
            template_renderer=self.template_renderer,
            llm_caller=self._call_llm,
        )

    async def _prepare_turn(
        self,
        db: AsyncSession,
        payload: AssistantTurnRequestDTO,
        *,
        owner_id: uuid.UUID,
        resolved_hooks: list[HookConfig] | None = None,
    ) -> PreparedAssistantTurn:
        return await prepare_assistant_turn(
            db,
            payload,
            owner_id=owner_id,
            resolved_hooks=resolved_hooks,
            config_loader=self.config_loader,
            template_renderer=self.template_renderer,
            project_service=self.project_service,
            assistant_preferences_service=self.assistant_preferences_service,
            assistant_rule_service=self.assistant_rule_service,
            assistant_agent_service=self.assistant_agent_service,
            assistant_skill_service=self.assistant_skill_service,
            assistant_hook_service=self.assistant_hook_service,
            assistant_tool_loop=self.assistant_tool_loop,
            turn_run_store=self.turn_run_store,
            project_document_capability_service=self.project_document_capability_service,
            resolve_llm_runtime=self._resolve_llm_runtime,
        )

    def _recover_or_start_turn(
        self,
        prepared: PreparedAssistantTurn,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantTurnResponseDTO | None:
        if self.turn_run_store is None:
            return None
        existing_run = self.turn_run_store.get_run(prepared.turn_context.run_id)
        if existing_run is not None:
            self._recover_existing_running_turn(
                prepared,
                existing_run=existing_run,
                owner_id=owner_id,
            )
            return recover_existing_turn(prepared=prepared, existing_run=existing_run)
        running_record = build_running_turn_record(
            prepared=prepared,
            owner_id=owner_id,
            runtime_claim_snapshot=self.runtime_claim_snapshot,
        )
        if self.turn_run_store.create_run(running_record):
            return None
        existing_run = self.turn_run_store.get_run(prepared.turn_context.run_id)
        if existing_run is None:
            raise ConfigurationError("Assistant turn run snapshot disappeared after create_run conflict")
        self._recover_existing_running_turn(
            prepared,
            existing_run=existing_run,
            owner_id=owner_id,
        )
        return recover_existing_turn(prepared=prepared, existing_run=existing_run)

    def _recover_existing_running_turn(
        self,
        prepared: PreparedAssistantTurn,
        *,
        existing_run,
        owner_id: uuid.UUID,
    ) -> None:
        if self.turn_run_store is None or existing_run.status != "running":
            return
        ensure_existing_turn_matches_request(
            prepared=prepared,
            existing_run=existing_run,
        )
        claim_state = resolve_runtime_claim_state(existing_run.runtime_claim_snapshot)
        if claim_state != "stale":
            return
        error = AssistantRuntimeTerminalError(
            code=(
                "stale_run_write_state_unknown"
                if existing_run.write_effective
                else "stale_run_interrupted"
            ),
            message=(
                "上次 turn 在写入后中断，当前不能安全重放，请刷新文稿状态后重新发起一次回复。"
                if existing_run.write_effective
                else "上次 turn 所在进程已中断，本轮已结束，请重新发起一次回复。"
            ),
            terminal_status="failed",
            write_effective=existing_run.write_effective,
        )
        self.turn_run_store.save_run(
            build_terminal_turn_record(
                prepared=prepared,
                owner_id=owner_id,
                existing_run=existing_run,
                error=error,
            )
        )
        raise error

    def _build_running_turn_record(
        self,
        prepared: PreparedAssistantTurn,
        *,
        owner_id: uuid.UUID,
        state_version: int = 1,
        provider_continuation_state: dict[str, Any] | None = None,
        pending_tool_calls_snapshot: tuple[dict[str, Any], ...] = (),
        write_effective: bool = False,
        started_at: datetime | None = None,
        updated_at: datetime | None = None,
        runtime_claim_snapshot: dict[str, Any] | None = None,
    ):
        return build_running_turn_record(
            prepared=prepared,
            owner_id=owner_id,
            state_version=state_version,
            provider_continuation_state=provider_continuation_state,
            pending_tool_calls_snapshot=pending_tool_calls_snapshot,
            write_effective=write_effective,
            started_at=started_at,
            updated_at=updated_at,
            runtime_claim_snapshot=runtime_claim_snapshot or self.runtime_claim_snapshot,
        )

    async def _run_prepare_on_error_hooks(
        self,
        db: AsyncSession,
        payload: AssistantTurnRequestDTO,
        *,
        hooks: list[HookConfig],
        error: Exception,
        owner_id: uuid.UUID,
    ) -> Exception | None:
        return await run_prepare_on_error_hooks(
            db,
            payload,
            hooks=hooks,
            error=error,
            owner_id=owner_id,
            run_on_error_hooks=self._run_on_error_hooks,
        )

    async def _run_prepared_on_error_hooks(
        self,
        db: AsyncSession,
        prepared: PreparedAssistantTurn,
        *,
        error: Exception,
        owner_id: uuid.UUID,
    ) -> Exception | None:
        return await run_prepared_on_error_hooks(
            db,
            prepared,
            error=error,
            owner_id=owner_id,
            run_on_error_hooks=self._run_on_error_hooks,
        )

    async def _run_before_turn_hooks(
        self,
        db: AsyncSession,
        prepared: PreparedAssistantTurn,
        *,
        owner_id: uuid.UUID,
    ) -> list[AssistantHookResultDTO]:
        return await run_before_turn_hooks(
            db,
            prepared,
            owner_id=owner_id,
            run_hook_event=self._run_hook_event,
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
            visible_tool_descriptors=prepared.visible_tool_descriptors,
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
        response = build_turn_response(
            prepared.spec,
            raw_output,
            content,
            before_results + after_results,
            prepared.turn_context,
        )
        return response

    def _build_stream_event_data(
        self,
        prepared: PreparedAssistantTurn,
        *,
        event_seq: int,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "run_id": str(prepared.turn_context.run_id),
            "conversation_id": prepared.turn_context.conversation_id,
            "client_turn_id": prepared.turn_context.client_turn_id,
            "event_seq": event_seq,
            "state_version": self._resolve_stream_state_version(
                prepared.turn_context.run_id,
                fallback=event_seq,
            ),
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        if extra:
            payload.update(extra)
        return payload

    def _resolve_stream_state_version(self, run_id: uuid.UUID, *, fallback: int) -> int:
        if self.turn_run_store is None:
            return fallback
        record = self.turn_run_store.get_run(run_id)
        if record is None:
            return fallback
        return record.state_version

    def _store_terminal_turn(
        self,
        prepared: PreparedAssistantTurn,
        *,
        owner_id: uuid.UUID,
        response: AssistantTurnResponseDTO | None = None,
        error: Exception | None = None,
    ) -> None:
        if self.turn_run_store is None:
            return
        existing_run = self.turn_run_store.get_run(prepared.turn_context.run_id)
        self.turn_run_store.save_run(
            build_terminal_turn_record(
                prepared=prepared,
                owner_id=owner_id,
                existing_run=existing_run,
                response=response,
                error=error,
            ),
        )

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
        return await run_assistant_hook_event(
            db,
            hooks,
            event,
            payload=payload,
            owner_id=owner_id,
            project_id=project_id,
            agent_id=agent_id,
            skill_id=skill_id,
            assistant_model=assistant_model,
            execute_hook_with_retry=self._execute_hook_with_retry,
        )

    async def _execute_hook_with_retry(
        self,
        context: AssistantHookExecutionContext,
        hook: HookConfig,
    ) -> Any:
        return await execute_assistant_hook_with_retry(
            context,
            hook,
            plugin_registry=self.plugin_registry,
        )

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
        await run_assistant_on_error_hooks(
            db,
            hooks,
            payload,
            error,
            owner_id=owner_id,
            project_id=project_id,
            agent_id=agent_id,
            skill_id=skill_id,
            assistant_model=assistant_model,
            run_hook_event=self._run_hook_event,
        )

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
        run_budget=None,
        tool_policy_decisions: tuple[Any, ...] = (),
        visible_tool_descriptors: tuple[Any, ...] = (),
        runtime_context: ResolvedAssistantLlmRuntime | None = None,
    ) -> dict[str, Any]:
        return await call_assistant_turn_llm(
            db,
            hooks,
            prompt=prompt,
            before_payload=before_payload,
            owner_id=owner_id,
            project_id=project_id,
            spec=spec,
            system_prompt=system_prompt,
            turn_context=turn_context,
            run_budget=run_budget,
            tool_policy_decisions=tuple(tool_policy_decisions),
            visible_tool_descriptors=tuple(visible_tool_descriptors),
            assistant_tool_loop=self.assistant_tool_loop,
            turn_run_store=self.turn_run_store,
            resolve_llm_runtime=self._resolve_llm_runtime,
            call_llm=self._call_llm,
            run_on_error_hooks=self._run_on_error_hooks,
            runtime_context=runtime_context,
        )

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
        runtime_context: ResolvedAssistantLlmRuntime | None = None,
        tools: list[dict[str, Any]] | None = None,
        should_stop: Callable[[], Awaitable[bool]] | None = None,
    ) -> AsyncIterator[LLMStreamEvent]:
        async for event in stream_assistant_turn_llm(
            db,
            hooks,
            prompt=prompt,
            before_payload=before_payload,
            owner_id=owner_id,
            project_id=project_id,
            spec=spec,
            system_prompt=system_prompt,
            tools=tools,
            should_stop=should_stop,
            resolve_llm_runtime=self._resolve_llm_runtime,
            call_llm_stream=self._call_llm_stream,
            run_on_error_hooks=self._run_on_error_hooks,
            runtime_context=runtime_context,
        ):
            yield event

    async def _stream_turn_with_tool_loop(
        self,
        db: AsyncSession,
        prepared: PreparedAssistantTurn,
        *,
        owner_id: uuid.UUID,
        should_stop: Callable[[], Awaitable[bool]] | None = None,
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        async for event_name, event_data in stream_assistant_turn_with_tool_loop(
            db,
            prepared,
            owner_id=owner_id,
            should_stop=should_stop,
            assistant_tool_loop=self.assistant_tool_loop,
            turn_run_store=self.turn_run_store,
            resolve_llm_runtime=self._resolve_llm_runtime,
            call_llm=self._call_llm,
            call_llm_stream=self._call_llm_stream,
            run_on_error_hooks=self._run_on_error_hooks,
            runtime_context=prepared.resolved_llm_runtime,
        ):
            yield event_name, event_data

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
        continuation_items: list[dict[str, Any]] | None = None,
        provider_continuation_state: dict[str, Any] | None = None,
        runtime_context: ResolvedAssistantLlmRuntime | None = None,
    ) -> dict[str, Any]:
        resolved_runtime = runtime_context or await self._resolve_llm_runtime(
            db,
            model=model,
            owner_id=owner_id,
            project_id=project_id,
        )
        return await call_assistant_llm(
            tool_provider=self.tool_provider,
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            resolved_runtime=resolved_runtime,
            response_format=response_format,
            tools=tools,
            continuation_items=continuation_items,
            provider_continuation_state=provider_continuation_state,
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
        runtime_context: ResolvedAssistantLlmRuntime | None = None,
        tools: list[dict[str, Any]] | None = None,
        continuation_items: list[dict[str, Any]] | None = None,
        provider_continuation_state: dict[str, Any] | None = None,
        should_stop: Callable[[], Awaitable[bool]] | None = None,
    ) -> AsyncIterator[LLMStreamEvent]:
        resolved_runtime = runtime_context or await self._resolve_llm_runtime(
            db,
            model=model,
            owner_id=owner_id,
            project_id=project_id,
        )
        async for event in stream_assistant_llm(
            tool_provider=self.tool_provider,
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            resolved_runtime=resolved_runtime,
            tools=tools,
            continuation_items=continuation_items,
            provider_continuation_state=provider_continuation_state,
            should_stop=should_stop,
        ):
            yield event

    async def _resolve_llm_runtime(
        self,
        db: AsyncSession,
        *,
        model: ModelConfig,
        owner_id: uuid.UUID,
        project_id: uuid.UUID | None,
    ) -> ResolvedAssistantLlmRuntime:
        return await resolve_assistant_llm_runtime(
            db,
            credential_service=self._resolve_credential_service(),
            model=model,
            owner_id=owner_id,
            project_id=project_id,
        )

    def _resolve_credential_service(self) -> CredentialService:
        if self._credential_service is None:
            self._credential_service = self.credential_service_factory()
        return self._credential_service
