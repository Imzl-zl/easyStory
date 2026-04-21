from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.schemas import HookConfig, ModelConfig
from app.modules.credential.service import CredentialService
from app.modules.project.service import ProjectDocumentCapabilityService, ProjectService
from app.shared.runtime.plugins.plugin_registry import PluginRegistry
from app.shared.runtime.template_renderer import SkillTemplateRenderer
from app.shared.runtime.tool_provider import ToolProvider
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
from .hooks_runtime.assistant_hook_agent_runtime import AssistantHookAgentRuntime, AssistantHookAgentRuntimeImpl
from .hooks_runtime.assistant_hook_support import AssistantHookExecutionContext
from .assistant_runtime_claim_support import build_current_runtime_claim_snapshot
from .turn.assistant_turn_runtime_support import PreparedAssistantTurn
from .assistant_llm_runtime_support import AssistantLlmTransportMode, ResolvedAssistantLlmRuntime
from .turn.assistant_turn_run_store import AssistantTurnRunStore
from .dto import AssistantHookResultDTO, AssistantTurnRequestDTO, AssistantTurnResponseDTO
from .preferences.preferences_service import AssistantPreferencesService
from .assistant_runtime_integration_support import build_plugin_registry, call_llm, call_llm_stream, call_turn_llm, call_turn_llm_stream, execute_hook_with_retry, resolve_credential_service, resolve_llm_runtime, run_hook_event, run_on_error_hooks, stream_turn_with_tool_loop
from .assistant_turn_service_support import execute_turn, build_running_turn_record_for_service, iterate_stream_turn, prepare_turn


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
        assistant_hook_agent_runtime: AssistantHookAgentRuntime | None = None,
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
        self.assistant_hook_agent_runtime = (
            assistant_hook_agent_runtime
            or AssistantHookAgentRuntimeImpl(
                assistant_agent_service=self.assistant_agent_service,
                assistant_skill_service=self.assistant_skill_service,
                assistant_preferences_service=self.assistant_preferences_service,
                assistant_rule_service=self.assistant_rule_service,
                template_renderer=self.template_renderer,
                llm_caller=lambda db, **kwargs: self._call_llm(db, **kwargs),
            )
        )
        self.plugin_registry = plugin_registry or build_plugin_registry(self)
        self._credential_service: CredentialService | None = None
        self.runtime_claim_snapshot = build_current_runtime_claim_snapshot()

    async def turn(
        self,
        db: AsyncSession,
        payload: AssistantTurnRequestDTO,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantTurnResponseDTO:
        return await execute_turn(
            self,
            db,
            payload,
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
        async for event_name, event_data in iterate_stream_turn(
            self,
            db,
            payload,
            owner_id=owner_id,
            should_stop=should_stop,
        ):
            yield AssistantStreamEvent(event_name, event_data)

    async def run_agent_hook(
        self,
        context: AssistantHookExecutionContext,
        *,
        agent_id: str,
        input_mapping: dict[str, str],
    ) -> Any:
        return await self.assistant_hook_agent_runtime.run(
            context,
            agent_id=agent_id,
            input_mapping=input_mapping,
        )

    async def _prepare_turn(
        self,
        db: AsyncSession,
        payload: AssistantTurnRequestDTO,
        *,
        owner_id: uuid.UUID,
        transport_mode: AssistantLlmTransportMode = "buffered",
        resolved_hooks: list[HookConfig] | None = None,
        ) -> PreparedAssistantTurn:
        return await prepare_turn(
            self,
            db,
            payload,
            owner_id=owner_id,
            transport_mode=transport_mode,
            resolved_hooks=resolved_hooks,
        )

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
        return build_running_turn_record_for_service(
            self,
            prepared,
            owner_id=owner_id,
            state_version=state_version,
            provider_continuation_state=provider_continuation_state,
            pending_tool_calls_snapshot=pending_tool_calls_snapshot,
            write_effective=write_effective,
            started_at=started_at,
            updated_at=updated_at,
            runtime_claim_snapshot=runtime_claim_snapshot,
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
        return await run_hook_event(
            self,
            db,
            hooks,
            event,
            payload=payload,
            owner_id=owner_id,
            project_id=project_id,
            agent_id=agent_id,
            skill_id=skill_id,
            assistant_model=assistant_model,
        )

    async def _execute_hook_with_retry(
        self,
        context: AssistantHookExecutionContext,
        hook: HookConfig,
    ) -> Any:
        return await execute_hook_with_retry(self, context, hook)

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
        await run_on_error_hooks(
            self,
            db,
            hooks,
            payload,
            error,
            owner_id=owner_id,
            project_id=project_id,
            agent_id=agent_id,
            skill_id=skill_id,
            assistant_model=assistant_model,
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
        spec,
        system_prompt: str | None,
        turn_context,
        run_budget=None,
        tool_policy_decisions: tuple[Any, ...] = (),
        visible_tool_descriptors: tuple[Any, ...] = (),
        runtime_context: ResolvedAssistantLlmRuntime | None = None,
    ) -> Any:
        return await call_turn_llm(
            self,
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
            tool_policy_decisions=tool_policy_decisions,
            visible_tool_descriptors=visible_tool_descriptors,
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
        spec,
        system_prompt: str | None,
        runtime_context: ResolvedAssistantLlmRuntime | None = None,
        tools: list[dict[str, Any]] | None = None,
        should_stop: Callable[[], Awaitable[bool]] | None = None,
    ) -> AsyncIterator[LLMStreamEvent]:
        async for event in call_turn_llm_stream(
            self,
            db,
            hooks,
            prompt=prompt,
            before_payload=before_payload,
            owner_id=owner_id,
            project_id=project_id,
            spec=spec,
            system_prompt=system_prompt,
            runtime_context=runtime_context,
            tools=tools,
            should_stop=should_stop,
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
        async for event_name, event_data in stream_turn_with_tool_loop(
            self,
            db,
            prepared,
            owner_id=owner_id,
            should_stop=should_stop,
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
        return await call_llm(
            self,
            db,
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            owner_id=owner_id,
            project_id=project_id,
            response_format=response_format,
            tools=tools,
            continuation_items=continuation_items,
            provider_continuation_state=provider_continuation_state,
            runtime_context=runtime_context,
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
        async for event in call_llm_stream(
            self,
            db,
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            owner_id=owner_id,
            project_id=project_id,
            runtime_context=runtime_context,
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
        return await resolve_llm_runtime(
            self,
            db,
            model=model,
            owner_id=owner_id,
            project_id=project_id,
        )

    def _resolve_credential_service(self) -> CredentialService:
        return resolve_credential_service(self)
