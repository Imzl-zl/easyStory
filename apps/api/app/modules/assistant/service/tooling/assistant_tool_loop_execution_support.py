from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from .assistant_tool_runtime_dto import AssistantToolResultEnvelope


async def execute_planned_tool_calls(
    *,
    planned_tool_calls: list[Any],
    state_version: int,
    initial_write_effective: bool,
    should_stop,
    execute_single_tool_call: Callable[[Any], Awaitable[AssistantToolResultEnvelope]],
    emit_iteration_item: Callable[..., None],
    build_iteration_item: Callable[..., Any],
) -> tuple[list[AssistantToolResultEnvelope], bool]:
    from .assistant_tool_loop_result_support import (
        AssistantToolStatePersistError,
        _build_cancelled_tool_call_result_payload,
        _build_failed_tool_call_result_payload,
        _build_state_persist_failed_tool_call_result_payload,
        _build_tool_call_result_payload,
        _build_tool_call_start_payload,
        _tool_result_committed_write,
    )
    from .assistant_tool_loop_runtime_support import raise_if_cancelled
    from app.shared.runtime.llm.interop.provider_interop_stream_support import StreamInterruptedError

    tool_results: list[AssistantToolResultEnvelope] = []
    write_effective = initial_write_effective
    for planned_tool_call in planned_tool_calls:
        await raise_if_cancelled(
            should_stop,
            write_effective=write_effective,
        )
        emit_iteration_item(
            build_iteration_item(
                event_name="tool_call_start",
                event_payload=_build_tool_call_start_payload(planned_tool_call.tool_call),
            ),
            state_version=state_version,
        )
        try:
            tool_result = await execute_single_tool_call(planned_tool_call)
        except StreamInterruptedError:
            emit_iteration_item(
                build_iteration_item(
                    event_name="tool_call_result",
                    event_payload=_build_cancelled_tool_call_result_payload(
                        planned_tool_call.tool_call,
                    ),
                ),
                state_version=state_version,
            )
            raise
        except AssistantToolStatePersistError as exc:
            emit_iteration_item(
                build_iteration_item(
                    event_name="tool_call_result",
                    event_payload=_build_state_persist_failed_tool_call_result_payload(
                        planned_tool_call.tool_call,
                        exc,
                    ),
                ),
                state_version=state_version,
            )
            raise
        except Exception as exc:
            emit_iteration_item(
                build_iteration_item(
                    event_name="tool_call_result",
                    event_payload=_build_failed_tool_call_result_payload(
                        planned_tool_call.tool_call,
                        exc,
                    ),
                ),
                state_version=state_version,
            )
            raise
        tool_results.append(tool_result)
        write_effective = write_effective or _tool_result_committed_write(
            descriptor=planned_tool_call.descriptor,
            result=tool_result,
        )
        emit_iteration_item(
            build_iteration_item(
                event_name="tool_call_result",
                event_payload=_build_tool_call_result_payload(
                    planned_tool_call.tool_call,
                    tool_result,
                    descriptor=planned_tool_call.descriptor,
                ),
            ),
            state_version=state_version,
        )
    return tool_results, write_effective


def build_post_tool_cycle_state(
    *,
    state: dict[str, Any],
    raw_output: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    tool_results: list[AssistantToolResultEnvelope],
    turn_context,
    continuation_support,
    output_items: list[dict[str, Any]],
    write_effective: bool,
    step_index: int,
) -> dict[str, Any]:
    from .assistant_tool_loop_output_support import (
        _build_tool_cycle_continuation_items,
        _build_tool_cycle_normalized_input_items,
        _build_tool_cycle_output_items,
        _resolve_provider_continuation_state,
    )

    cycle_output_items = _build_tool_cycle_output_items(
        turn_context=turn_context,
        start_index=len(output_items),
        tool_calls=tool_calls,
        tool_results=tool_results,
    )
    normalized_input_items = [
        *state.get("normalized_input_items", []),
        *_build_tool_cycle_normalized_input_items(
            raw_output=raw_output,
            tool_calls=tool_calls,
            tool_results=tool_results,
        ),
    ]
    cycle_continuation_items = _build_tool_cycle_continuation_items(
        raw_output=raw_output,
        tool_calls=tool_calls,
        tool_results=tool_results,
        tool_cycle_index=state.get("tool_cycle_index", 0),
    )
    continuation_items = [*state.get("continuation_items", []), *cycle_continuation_items]
    provider_continuation_state = _resolve_provider_continuation_state(
        raw_output=raw_output,
        latest_items=cycle_continuation_items,
        continuation_support=continuation_support,
    )
    return {
        "output_items": [*output_items, *cycle_output_items],
        "normalized_input_items": normalized_input_items,
        "continuation_items": continuation_items,
        "provider_continuation_state": provider_continuation_state,
        "write_effective": write_effective,
        "step_index": step_index,
        "tool_cycle_index": state.get("tool_cycle_index", 0) + 1,
        "current_tool_calls": [],
        "current_raw_output": None,
        "current_raw_output_already_streamed": False,
    }
