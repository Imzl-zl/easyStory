from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..errors import ConfigurationError
from .llm_protocol_types import NormalizedLLMResponse
from .llm_response_validation import raise_if_empty_tool_response
from .llm_stream_events import (
    ParsedStreamEvent,
    build_truncated_stream_message,
    extract_stream_truncation_reason,
    synthesize_stream_terminal_response,
)
from .llm_terminal_assembly import build_stream_completion

DEFAULT_EMPTY_STREAM_RESPONSE_MESSAGE = "模型没有返回可展示的内容，请稍后重试。"


@dataclass
class BackendStreamCompletionState:
    text_parts: list[str] = field(default_factory=list)
    raw_event_tuples: list[tuple[str | None, dict[str, Any]]] = field(default_factory=list)
    truncation_reason: str | None = None
    saw_terminal_event: bool = False
    terminal_response: NormalizedLLMResponse | None = None


def record_backend_stream_event(
    state: BackendStreamCompletionState,
    *,
    recorded_event_name: str | None,
    raw_payload: dict[str, Any],
    parsed_event: ParsedStreamEvent,
    terminal_event_detected: bool,
) -> str | None:
    state.raw_event_tuples.append((recorded_event_name, raw_payload))
    if state.truncation_reason is None:
        state.truncation_reason = extract_stream_truncation_reason(parsed_event.stop_reason)
    if not state.saw_terminal_event:
        state.saw_terminal_event = terminal_event_detected
    if parsed_event.terminal_response is not None:
        state.terminal_response = parsed_event.terminal_response
    if not parsed_event.delta:
        return None
    state.text_parts.append(parsed_event.delta)
    return parsed_event.delta


def finalize_backend_stream_completion(
    state: BackendStreamCompletionState,
    *,
    api_dialect: str,
    tool_name_aliases: dict[str, str],
    has_tools: bool,
    incomplete_stream_message: str,
    empty_stream_message: str = DEFAULT_EMPTY_STREAM_RESPONSE_MESSAGE,
) -> NormalizedLLMResponse:
    synthesized_terminal = synthesize_stream_terminal_response(
        api_dialect,
        raw_events=state.raw_event_tuples,
        tool_name_aliases=tool_name_aliases,
    )
    if synthesized_terminal is not None:
        state.terminal_response = synthesized_terminal
    normalized = build_stream_completion(
        api_dialect=api_dialect,
        text_parts=state.text_parts,
        terminal_response=state.terminal_response,
    )
    if normalized is None:
        raise_if_empty_tool_response(has_tools=has_tools, content="", tool_calls=[])
        raise ConfigurationError(empty_stream_message)
    if state.truncation_reason is not None:
        raise ConfigurationError(build_truncated_stream_message(state.truncation_reason))
    raise_if_empty_tool_response(
        has_tools=has_tools,
        content=normalized.content,
        tool_calls=normalized.tool_calls,
    )
    if not state.saw_terminal_event:
        raise ConfigurationError(incomplete_stream_message)
    return normalized
