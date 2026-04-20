from __future__ import annotations

from collections.abc import Callable
from typing import Any, TYPE_CHECKING, TypedDict

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.llm_tool_provider import LLMGenerateToolResponse

from .assistant_tool_loop_context_support import _record_tool_loop_state
from .assistant_tool_loop_output_support import _build_usage_totals_state
from .assistant_tool_runtime_dto import AssistantToolLoopStateRecorder

if TYPE_CHECKING:
    from ..turn.assistant_turn_runtime_support import AssistantTurnContext


class AssistantToolLoopUsageState(TypedDict):
    input_tokens: int
    output_tokens: int
    total_tokens: int


class AssistantToolLoopGraphState(TypedDict, total=False):
    iteration: int
    pending_output: LLMGenerateToolResponse | None
    pending_output_already_streamed: bool
    current_raw_output: LLMGenerateToolResponse | None
    current_raw_output_already_streamed: bool
    current_tool_calls: list[dict[str, Any]]
    output_items: list[dict[str, Any]]
    continuation_items: list[dict[str, Any]]
    normalized_input_items: list[dict[str, Any]]
    provider_continuation_state: dict[str, Any] | None
    continuation_request_snapshot: dict[str, Any] | None
    continuation_compaction_snapshot: dict[str, Any] | None
    write_effective: bool
    state_version: int
    step_index: int
    tool_cycle_index: int
    usage: AssistantToolLoopUsageState
    request_continuation_items: list[dict[str, Any]]
    request_provider_state: dict[str, Any] | None


TOOL_LOOP_RECURSION_STEP_WIDTH = 5
TOOL_LOOP_RECURSION_BUFFER = 10
INITIAL_TOOL_LOOP_STATE_VERSION = 1


def build_initial_graph_state(
    turn_context: "AssistantTurnContext",
    *,
    initial_raw_output: LLMGenerateToolResponse | None,
) -> AssistantToolLoopGraphState:
    return {
        "iteration": 0,
        "pending_output": initial_raw_output,
        "pending_output_already_streamed": False,
        "current_raw_output": None,
        "current_raw_output_already_streamed": False,
        "current_tool_calls": [],
        "output_items": [],
        "continuation_items": [],
        "normalized_input_items": list(getattr(turn_context, "normalized_input_items", [])),
        "provider_continuation_state": None,
        "continuation_request_snapshot": None,
        "continuation_compaction_snapshot": None,
        "write_effective": False,
        "state_version": INITIAL_TOOL_LOOP_STATE_VERSION,
        "step_index": 0,
        "tool_cycle_index": 0,
        "usage": _build_usage_totals_state(),
        "request_continuation_items": [],
        "request_provider_state": None,
    }


def record_graph_state(
    state_recorder: AssistantToolLoopStateRecorder | None,
    *,
    current_state_version: int,
    provider_continuation_state: dict[str, Any] | None,
    normalized_input_items: list[dict[str, Any]],
    continuation_request_snapshot: dict[str, Any] | None,
    continuation_compaction_snapshot: dict[str, Any] | None,
    write_effective: bool,
    pending_tool_calls_snapshot: tuple[dict[str, Any], ...],
) -> int:
    next_state_version = current_state_version + 1
    _record_tool_loop_state(
        state_recorder,
        pending_tool_calls_snapshot=pending_tool_calls_snapshot,
        provider_continuation_state=provider_continuation_state,
        normalized_input_items_snapshot=tuple(normalized_input_items),
        continuation_request_snapshot=continuation_request_snapshot,
        continuation_compaction_snapshot=continuation_compaction_snapshot,
        write_effective=write_effective,
    )
    return next_state_version


def require_current_raw_output(
    state: AssistantToolLoopGraphState,
) -> LLMGenerateToolResponse:
    raw_output = state.get("current_raw_output")
    if raw_output is None:
        raise ConfigurationError("Assistant tool loop runtime missing current raw output")
    return raw_output


def serialize_iteration_item(
    item: Any,
    *,
    state_version: int | None,
) -> dict[str, Any]:
    event_payload = item.event_payload
    if event_payload is not None and state_version is not None:
        event_payload = {**event_payload, "state_version": state_version}
    return {
        "kind": "assistant_tool_loop_iteration_item",
        "event_name": item.event_name,
        "event_payload": event_payload,
        "raw_output": item.raw_output,
        "raw_output_already_streamed": item.raw_output_already_streamed,
    }


def deserialize_iteration_item(
    payload: Any,
    *,
    build_iteration_item: Callable[..., Any],
) -> Any | None:
    if not isinstance(payload, dict):
        return None
    if payload.get("kind") != "assistant_tool_loop_iteration_item":
        return None
    return build_iteration_item(
        event_name=payload.get("event_name"),
        event_payload=payload.get("event_payload"),
        raw_output=payload.get("raw_output"),
        raw_output_already_streamed=bool(payload.get("raw_output_already_streamed")),
    )
