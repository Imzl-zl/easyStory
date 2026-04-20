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
