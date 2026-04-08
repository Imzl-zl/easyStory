from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry.schemas import HookConfig
from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.llm_tool_provider import LLMGenerateToolResponse, LLMStreamEvent
from app.shared.runtime.llm.interop.provider_interop_stream_support import StreamInterruptedError

from ..assistant_execution_support import AssistantExecutionSpec
from ..assistant_llm_runtime_support import (
    build_tool_loop_model_caller,
    build_tool_loop_stream_model_caller,
)
from ..tooling.assistant_tool_loop import AssistantToolLoop
from ..tooling.assistant_tool_runtime_dto import AssistantToolLoopStateSnapshot
from .assistant_turn_run_store import AssistantTurnRunStore
from .assistant_turn_run_support import update_running_turn_record
from .assistant_turn_runtime_support import PreparedAssistantTurn


@dataclass
class _InitialToolLoopStreamCapture:
    raw_output: LLMGenerateToolResponse | None = None


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


def has_tool_calls(raw_output: LLMGenerateToolResponse) -> bool:
    tool_calls = raw_output.get("tool_calls")
    return isinstance(tool_calls, list) and bool(tool_calls)


def build_buffered_final_chunk_payload(
    raw_output: LLMGenerateToolResponse,
) -> dict[str, Any] | None:
    content = raw_output.get("content")
    if not isinstance(content, str) or not content:
        return None
    return {"delta": content, "chunk_kind": "buffered_final"}


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
    tool_schemas = assistant_tool_loop.resolve_tool_schemas(
        turn_context=prepared.turn_context,
        project_id=prepared.project_id,
        visible_descriptors=prepared.visible_tool_descriptors,
    )
    if not tool_schemas:
        raise ConfigurationError("Assistant tool loop streaming requires visible tools")
    resolved_runtime = runtime_context or await resolve_llm_runtime(
        db,
        model=prepared.spec.model,
        owner_id=owner_id,
        project_id=prepared.project_id,
    )
    try:
        capture = _InitialToolLoopStreamCapture()
        async for event_name, event_payload in _stream_initial_tool_loop_response(
            db,
            prepared,
            tool_schemas=tool_schemas,
            owner_id=owner_id,
            should_stop=should_stop,
            runtime_context=resolved_runtime,
            call_llm_stream=call_llm_stream,
            capture=capture,
        ):
            yield event_name, event_payload
        raw_output = capture.raw_output
        if raw_output is None:
            raise ConfigurationError("Streaming response completed without initial output")
        if not has_tool_calls(raw_output):
            yield "final_output", raw_output
            return
        async for event_name, event_payload in _stream_tool_loop_followup(
            db,
            prepared,
            assistant_tool_loop=assistant_tool_loop,
            turn_run_store=turn_run_store,
            owner_id=owner_id,
            should_stop=should_stop,
            runtime_context=resolved_runtime,
            call_llm=call_llm,
            call_llm_stream=call_llm_stream,
            raw_output=raw_output,
        ):
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


async def _stream_initial_tool_loop_response(
    db: AsyncSession,
    prepared: PreparedAssistantTurn,
    *,
    tool_schemas: list[dict[str, Any]],
    owner_id: uuid.UUID,
    should_stop: Callable[[], Awaitable[bool]] | None,
    runtime_context,
    call_llm_stream,
    capture: _InitialToolLoopStreamCapture,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    async for event in call_llm_stream(
        db,
        prompt=prepared.prompt,
        system_prompt=prepared.system_prompt,
        model=prepared.spec.model,
        owner_id=owner_id,
        project_id=prepared.project_id,
        runtime_context=runtime_context,
        tools=tool_schemas,
        should_stop=should_stop,
    ):
        if event.delta:
            yield "chunk", {"delta": event.delta}
            continue
        capture.raw_output = event.response


async def _stream_tool_loop_followup(
    db: AsyncSession,
    prepared: PreparedAssistantTurn,
    *,
    assistant_tool_loop: AssistantToolLoop,
    turn_run_store: AssistantTurnRunStore | None,
    owner_id: uuid.UUID,
    should_stop: Callable[[], Awaitable[bool]] | None,
    runtime_context,
    call_llm,
    call_llm_stream,
    raw_output: LLMGenerateToolResponse,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    async for item in assistant_tool_loop.iterate(
        db,
        turn_context=prepared.turn_context,
        owner_id=owner_id,
        project_id=prepared.project_id,
        prompt=prepared.prompt,
        system_prompt=prepared.system_prompt,
        continuation_support=runtime_context.continuation_support,
        model_caller=build_tool_loop_model_caller(
            llm_caller=call_llm,
            db=db,
            model=prepared.spec.model,
            owner_id=owner_id,
            project_id=prepared.project_id,
            runtime_context=runtime_context,
        ),
        stream_model_caller=build_tool_loop_stream_model_caller(
            llm_stream_caller=call_llm_stream,
            db=db,
            model=prepared.spec.model,
            owner_id=owner_id,
            project_id=prepared.project_id,
            runtime_context=runtime_context,
            should_stop=should_stop,
        ),
        initial_raw_output=raw_output,
        run_budget=prepared.run_budget,
        tool_policy_decisions=prepared.tool_policy_decisions,
        visible_descriptors=prepared.visible_tool_descriptors,
        state_recorder=build_turn_tool_loop_state_recorder(
            turn_run_store=turn_run_store,
            run_id=prepared.turn_context.run_id,
        ),
        should_stop=should_stop,
    ):
        if item.event_name is not None and item.event_payload is not None:
            yield item.event_name, item.event_payload
            continue
        if item.raw_output is None:
            continue
        buffered_chunk = (
            None
            if item.raw_output_already_streamed
            else build_buffered_final_chunk_payload(item.raw_output)
        )
        if buffered_chunk is not None:
            yield "chunk", buffered_chunk
        yield "final_output", item.raw_output
