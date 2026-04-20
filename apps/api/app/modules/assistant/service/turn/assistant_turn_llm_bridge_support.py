from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry.schemas import HookConfig
from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.llm_tool_provider import LLMGenerateToolResponse, LLMStreamEvent
from app.shared.runtime.llm.interop.provider_interop_stream_support import StreamInterruptedError

from ..assistant_execution_support import AssistantExecutionSpec
from ..assistant_llm_runtime_support import build_tool_loop_model_caller
from ..tooling.assistant_tool_loop import AssistantToolLoop
from ..tooling.assistant_tool_runtime_dto import AssistantToolLoopStateSnapshot
from .assistant_turn_run_store import AssistantTurnRunStore
from .assistant_turn_run_support import update_running_turn_record
from .assistant_turn_runtime_support import PreparedAssistantTurn


def build_turn_tool_loop_state_recorder(
    *,
    turn_run_store: AssistantTurnRunStore | None,
    run_id: uuid.UUID,
) -> Callable[[AssistantToolLoopStateSnapshot], None] | None:
    if turn_run_store is None:
        return None

    def recorder(snapshot: AssistantToolLoopStateSnapshot) -> None:
        existing_run = turn_run_store.get_run(run_id)
        if existing_run is None or existing_run.status != "running":
            return
        turn_run_store.save_run(
            update_running_turn_record(
                existing_run=existing_run,
                snapshot=snapshot,
            )
        )

    return recorder


def should_stream_with_tool_loop(
    *,
    assistant_tool_loop: AssistantToolLoop | None,
    prepared: PreparedAssistantTurn,
) -> bool:
    return assistant_tool_loop is not None and bool(prepared.visible_tool_descriptors)


async def call_assistant_turn_llm(
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
    run_budget,
    tool_policy_decisions: tuple[Any, ...],
    visible_tool_descriptors: tuple[Any, ...],
    assistant_tool_loop: AssistantToolLoop | None,
    turn_run_store: AssistantTurnRunStore | None,
    resolve_llm_runtime,
    call_llm,
    run_on_error_hooks,
    runtime_context=None,
) -> LLMGenerateToolResponse:
    try:
        resolved_runtime = runtime_context or await resolve_llm_runtime(
            db,
            model=spec.model,
            owner_id=owner_id,
            project_id=project_id,
        )
        if assistant_tool_loop is not None:
            loop_result = await assistant_tool_loop.execute(
                db,
                turn_context=turn_context,
                owner_id=owner_id,
                project_id=project_id,
                prompt=prompt,
                system_prompt=system_prompt,
                continuation_support=resolved_runtime.continuation_support,
                model_caller=build_tool_loop_model_caller(
                    llm_caller=call_llm,
                    db=db,
                    model=spec.model,
                    owner_id=owner_id,
                    project_id=project_id,
                    runtime_context=resolved_runtime,
                ),
                run_budget=run_budget,
                tool_policy_decisions=tuple(tool_policy_decisions),
                visible_descriptors=tuple(visible_tool_descriptors),
                state_recorder=build_turn_tool_loop_state_recorder(
                    turn_run_store=turn_run_store,
                    run_id=turn_context.run_id,
                ),
            )
            return loop_result.raw_output
        return await call_llm(
            db,
            prompt=prompt,
            system_prompt=system_prompt,
            model=spec.model,
            owner_id=owner_id,
            project_id=project_id,
            runtime_context=resolved_runtime,
        )
    except Exception as exc:
        await run_on_error_hooks(
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


async def stream_assistant_turn_llm(
    db: AsyncSession,
    hooks: list[HookConfig],
    *,
    prompt: str,
    before_payload: dict[str, Any],
    owner_id: uuid.UUID,
    project_id: uuid.UUID | None,
    spec: AssistantExecutionSpec,
    system_prompt: str | None,
    tools: list[dict[str, Any]] | None,
    should_stop: Callable[[], Awaitable[bool]] | None,
    resolve_llm_runtime,
    call_llm_stream,
    run_on_error_hooks,
    runtime_context=None,
) -> AsyncIterator[LLMStreamEvent]:
    try:
        resolved_runtime = runtime_context or await resolve_llm_runtime(
            db,
            model=spec.model,
            owner_id=owner_id,
            project_id=project_id,
        )
        async for event in call_llm_stream(
            db,
            prompt=prompt,
            system_prompt=system_prompt,
            model=spec.model,
            owner_id=owner_id,
            project_id=project_id,
            runtime_context=resolved_runtime,
            tools=tools,
            should_stop=should_stop,
        ):
            yield event
    except StreamInterruptedError:
        raise
    except Exception as exc:
        await run_on_error_hooks(
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


async def stream_assistant_turn_with_tool_loop(
    db: AsyncSession,
    prepared: PreparedAssistantTurn,
    *,
    owner_id: uuid.UUID,
    should_stop: Callable[[], Awaitable[bool]] | None,
    assistant_tool_loop: AssistantToolLoop | None,
    turn_run_store: AssistantTurnRunStore | None,
    resolve_llm_runtime,
    call_llm,
    call_llm_stream,
    run_on_error_hooks,
    runtime_context=None,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    if assistant_tool_loop is None:
        raise ConfigurationError("Assistant tool loop is not configured")
    from .assistant_turn_tool_stream_runtime import AssistantTurnToolStreamRuntime

    try:
        runtime = AssistantTurnToolStreamRuntime(
            owner_id=owner_id,
            db=db,
            prepared=prepared,
            should_stop=should_stop,
            assistant_tool_loop=assistant_tool_loop,
            turn_run_store=turn_run_store,
            resolve_llm_runtime=resolve_llm_runtime,
            call_llm=call_llm,
            call_llm_stream=call_llm_stream,
            runtime_context=runtime_context,
        )
        async for event_name, event_payload in runtime.iterate():
            yield event_name, event_payload
    except StreamInterruptedError:
        raise
    except Exception as exc:
        await run_on_error_hooks(
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
