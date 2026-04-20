from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry.schemas import HookConfig, ModelConfig
from app.modules.credential.service import CredentialService
from app.shared.runtime.llm.llm_tool_provider import LLMGenerateToolResponse, LLMStreamEvent

from .assistant_execution_support import AssistantExecutionSpec
from .assistant_llm_runtime_support import (
    ResolvedAssistantLlmRuntime,
    call_assistant_llm,
    resolve_assistant_llm_runtime,
    stream_assistant_llm,
)
from .hooks_runtime.assistant_hook_providers import build_assistant_plugin_registry
from .hooks_runtime.assistant_hook_runtime_support import (
    execute_assistant_hook_with_retry,
    run_assistant_hook_event,
    run_assistant_on_error_hooks,
)
from .hooks_runtime.assistant_hook_support import AssistantHookExecutionContext
from .turn.assistant_turn_llm_bridge_support import (
    call_assistant_turn_llm,
    stream_assistant_turn_llm,
    stream_assistant_turn_with_tool_loop,
)
from .turn.assistant_turn_runtime_support import PreparedAssistantTurn

if TYPE_CHECKING:
    from .assistant_service import AssistantService


async def run_hook_event(
    service: "AssistantService",
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
) -> list[Any]:
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
        execute_hook_with_retry=service._execute_hook_with_retry,
    )


async def execute_hook_with_retry(
    service: "AssistantService",
    context: AssistantHookExecutionContext,
    hook: HookConfig,
) -> Any:
    return await execute_assistant_hook_with_retry(
        context,
        hook,
        plugin_registry=service.plugin_registry,
    )


async def run_on_error_hooks(
    service: "AssistantService",
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
        run_hook_event=service._run_hook_event,
    )


async def call_turn_llm(
    service: "AssistantService",
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
) -> LLMGenerateToolResponse:
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
        assistant_tool_loop=service.assistant_tool_loop,
        turn_run_store=service.turn_run_store,
        resolve_llm_runtime=service._resolve_llm_runtime,
        call_llm=service._call_llm,
        run_on_error_hooks=service._run_on_error_hooks,
        runtime_context=runtime_context,
    )


async def call_turn_llm_stream(
    service: "AssistantService",
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
        resolve_llm_runtime=service._resolve_llm_runtime,
        call_llm_stream=service._call_llm_stream,
        run_on_error_hooks=service._run_on_error_hooks,
        runtime_context=runtime_context,
    ):
        yield event


async def stream_turn_with_tool_loop(
    service: "AssistantService",
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
        assistant_tool_loop=service.assistant_tool_loop,
        turn_run_store=service.turn_run_store,
        resolve_llm_runtime=service._resolve_llm_runtime,
        call_llm=service._call_llm,
        call_llm_stream=service._call_llm_stream,
        run_on_error_hooks=service._run_on_error_hooks,
        runtime_context=prepared.resolved_llm_runtime,
    ):
        yield event_name, event_data


async def call_llm(
    service: "AssistantService",
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
    resolved_runtime = runtime_context or await resolve_llm_runtime(
        service,
        db,
        model=model,
        owner_id=owner_id,
        project_id=project_id,
    )
    return await call_assistant_llm(
        tool_provider=service.tool_provider,
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        resolved_runtime=resolved_runtime,
        response_format=response_format,
        tools=tools,
        continuation_items=continuation_items,
        provider_continuation_state=provider_continuation_state,
    )


async def call_llm_stream(
    service: "AssistantService",
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
    resolved_runtime = runtime_context or await resolve_llm_runtime(
        service,
        db,
        model=model,
        owner_id=owner_id,
        project_id=project_id,
    )
    async for event in stream_assistant_llm(
        tool_provider=service.tool_provider,
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


async def resolve_llm_runtime(
    service: "AssistantService",
    db: AsyncSession,
    *,
    model: ModelConfig,
    owner_id: uuid.UUID,
    project_id: uuid.UUID | None,
) -> ResolvedAssistantLlmRuntime:
    return await resolve_assistant_llm_runtime(
        db,
        credential_service=resolve_credential_service(service),
        model=model,
        owner_id=owner_id,
        project_id=project_id,
    )


def resolve_credential_service(service: "AssistantService") -> CredentialService:
    if service._credential_service is None:
        service._credential_service = service.credential_service_factory()
    return service._credential_service


def build_plugin_registry(
    service: "AssistantService",
):
    return build_assistant_plugin_registry(
        service,
        mcp_server_resolver=lambda context, server_id: service.assistant_mcp_service.resolve_mcp_server(
            server_id,
            owner_id=context.owner_id,
            project_id=context.project_id,
        ),
    )
