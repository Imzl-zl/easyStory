from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.schemas import HookConfig, ModelConfig
from app.modules.credential.service import CredentialService
from app.modules.credential.service.credential_connection_support import build_runtime_credential_payload
from app.modules.project.service import ProjectService
from app.shared.runtime import PluginRegistry, SkillTemplateRenderer, ToolProvider
from app.shared.runtime.llm_tool_provider import LLM_GENERATE_TOOL

from .assistant_hook_providers import build_assistant_plugin_registry
from .assistant_hook_support import (
    AssistantHookExecutionContext,
    matches_hook_condition,
    normalize_hook_result,
    resolve_assistant_hooks_for_event,
    serialize_hook_error,
)
from .assistant_execution_support import (
    build_after_assistant_payload,
    build_before_assistant_payload,
    build_hook_agent_variables,
    build_turn_response,
    dump_turn_messages,
    hook_agent_response_format,
    render_prompt,
    require_agent_skill,
    require_text_output,
    resolve_execution_spec,
    resolve_hook_agent_output,
    resolve_model,
    validate_retry_policy,
)
from .dto import AssistantHookResultDTO, AssistantTurnRequestDTO, AssistantTurnResponseDTO


class AssistantService:
    def __init__(
        self,
        *,
        config_loader: ConfigLoader,
        credential_service_factory: Callable[[], CredentialService],
        project_service: ProjectService,
        tool_provider: ToolProvider,
        template_renderer: SkillTemplateRenderer,
        plugin_registry: PluginRegistry | None = None,
    ) -> None:
        self.config_loader = config_loader
        self.credential_service_factory = credential_service_factory
        self.project_service = project_service
        self.tool_provider = tool_provider
        self.template_renderer = template_renderer
        self.plugin_registry = plugin_registry or build_assistant_plugin_registry(self, config_loader=config_loader)
        self._credential_service: CredentialService | None = None

    async def turn(
        self,
        db: AsyncSession,
        payload: AssistantTurnRequestDTO,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantTurnResponseDTO:
        project_id = await self._resolve_project_scope(db, payload.project_id, owner_id=owner_id)
        spec = resolve_execution_spec(self.config_loader, payload)
        prompt = render_prompt(
            config_loader=self.config_loader,
            template_renderer=self.template_renderer,
            skill=spec.skill,
            payload=payload,
        )
        hooks = [self.config_loader.load_hook(hook_id) for hook_id in payload.hook_ids]
        messages = dump_turn_messages(payload)
        before_payload = build_before_assistant_payload(spec, payload, project_id, messages)
        before_results = await self._run_hook_event(
            db,
            hooks,
            "before_assistant_response",
            payload=before_payload,
            owner_id=owner_id,
            project_id=project_id,
            agent_id=spec.agent_id,
            skill_id=spec.skill.id,
        )
        raw_output = await self._call_turn_llm(
            db,
            hooks,
            prompt=prompt,
            before_payload=before_payload,
            owner_id=owner_id,
            project_id=project_id,
            spec=spec,
        )
        content = require_text_output(raw_output.get("content"))
        after_payload = build_after_assistant_payload(spec, payload, project_id, messages, content)
        after_results = await self._run_hook_event(
            db,
            hooks,
            "after_assistant_response",
            payload=after_payload,
            owner_id=owner_id,
            project_id=project_id,
            agent_id=spec.agent_id,
            skill_id=spec.skill.id,
        )
        return build_turn_response(spec, raw_output, content, before_results + after_results)

    async def run_agent_hook(
        self,
        context: AssistantHookExecutionContext,
        *,
        agent_id: str,
        input_mapping: dict[str, str],
    ) -> Any:
        agent = self.config_loader.load_agent(agent_id)
        skill = require_agent_skill(self.config_loader, agent)
        variables = build_hook_agent_variables(context, input_mapping)
        prompt = self.template_renderer.render(skill.prompt, variables)
        model = resolve_model(agent.model or skill.model, None, context_label=f"Hook agent {agent.id}")
        raw_output = await self._call_llm(
            context.db,
            prompt=prompt,
            system_prompt=agent.system_prompt,
            model=model,
            owner_id=context.owner_id,
            project_id=context.project_id,
            response_format=hook_agent_response_format(agent),
        )
        return resolve_hook_agent_output(agent, raw_output.get("content"))

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
        skill_id: str,
    ) -> list[AssistantHookResultDTO]:
        context = AssistantHookExecutionContext(
            db=db,
            event=event,
            owner_id=owner_id,
            payload=payload,
            assistant_agent_id=agent_id,
            assistant_skill_id=skill_id,
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
        skill_id: str,
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
        spec,
    ) -> dict[str, Any]:
        try:
            return await self._call_llm(
                db,
                prompt=prompt,
                system_prompt=spec.system_prompt,
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
                skill_id=spec.skill.id,
            )
            raise

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
            },
        )

    def _resolve_credential_service(self) -> CredentialService:
        if self._credential_service is None:
            self._credential_service = self.credential_service_factory()
        return self._credential_service
