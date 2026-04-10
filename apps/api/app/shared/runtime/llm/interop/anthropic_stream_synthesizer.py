from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ..llm_protocol import NormalizedLLMResponse
from ..llm_protocol_responses import parse_generation_response


@dataclass
class AnthropicSynthesisState:
    blocks_by_index: dict[int, dict[str, Any]] = field(default_factory=dict)
    input_json_by_index: dict[int, str] = field(default_factory=dict)
    response_id: str | None = None
    stop_reason: str | None = None
    usage: dict[str, Any] | None = None


def synthesize_anthropic_terminal_response(
    raw_events: list[tuple[str | None, dict[str, Any]]],
    *,
    tool_name_aliases: dict[str, str],
) -> NormalizedLLMResponse | None:
    state = AnthropicSynthesisState()
    for event_name, payload in raw_events:
        _apply_anthropic_event(state, event_name, payload)
    content_blocks = _build_anthropic_content_blocks(state)
    if not any(isinstance(block, dict) and block.get("type") == "tool_use" for block in content_blocks):
        return None
    reconstructed_payload: dict[str, Any] = {
        "content": content_blocks,
        "stop_reason": state.stop_reason or "tool_use",
    }
    if state.response_id is not None:
        reconstructed_payload["id"] = state.response_id
    if state.usage is not None:
        reconstructed_payload["usage"] = state.usage
    return parse_generation_response(
        "anthropic_messages",
        reconstructed_payload,
        tool_name_aliases=tool_name_aliases,
    )


def _apply_anthropic_event(
    state: AnthropicSynthesisState,
    event_name: str | None,
    payload: dict[str, Any],
) -> None:
    resolved_event_name = event_name or _read_optional_string(payload.get("type"))
    if resolved_event_name == "message_start":
        _apply_anthropic_message_start(state, payload)
        return
    if resolved_event_name == "message_delta":
        _apply_anthropic_message_delta(state, payload)
        return
    if resolved_event_name == "content_block_start":
        _apply_anthropic_content_block_start(state, payload)
        return
    if resolved_event_name == "content_block_delta":
        _apply_anthropic_content_block_delta(state, payload)


def _apply_anthropic_message_start(
    state: AnthropicSynthesisState,
    payload: dict[str, Any],
) -> None:
    message = payload.get("message")
    if not isinstance(message, dict):
        return
    response_id = _read_optional_string(message.get("id"))
    if response_id is not None:
        state.response_id = response_id
    usage = message.get("usage")
    if isinstance(usage, dict):
        state.usage = dict(usage)


def _apply_anthropic_message_delta(
    state: AnthropicSynthesisState,
    payload: dict[str, Any],
) -> None:
    usage = payload.get("usage")
    if isinstance(usage, dict):
        state.usage = dict(usage)
    delta = payload.get("delta")
    if not isinstance(delta, dict):
        return
    stop_reason = _read_optional_string(delta.get("stop_reason"))
    if stop_reason is not None:
        state.stop_reason = stop_reason


def _apply_anthropic_content_block_start(
    state: AnthropicSynthesisState,
    payload: dict[str, Any],
) -> None:
    index = _read_content_block_index(payload.get("index"))
    if index is None:
        return
    content_block = payload.get("content_block")
    if not isinstance(content_block, dict):
        return
    block_copy = dict(content_block)
    if block_copy.get("type") == "text":
        block_copy["text"] = _read_optional_string(block_copy.get("text")) or ""
    if block_copy.get("type") == "tool_use":
        initial_input = block_copy.get("input")
        if isinstance(initial_input, dict) and initial_input:
            state.input_json_by_index[index] = json.dumps(
                initial_input,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        elif isinstance(initial_input, str):
            state.input_json_by_index[index] = initial_input
    state.blocks_by_index[index] = block_copy


def _apply_anthropic_content_block_delta(
    state: AnthropicSynthesisState,
    payload: dict[str, Any],
) -> None:
    index = _read_content_block_index(payload.get("index"))
    if index is None:
        return
    block = state.blocks_by_index.get(index)
    if not isinstance(block, dict):
        return
    delta = payload.get("delta")
    if not isinstance(delta, dict):
        return
    delta_type = _read_optional_string(delta.get("type"))
    if delta_type == "text_delta" and block.get("type") == "text":
        text = _read_optional_string(delta.get("text"))
        if text is not None:
            block["text"] = f"{_read_optional_string(block.get('text')) or ''}{text}"
        return
    if delta_type == "input_json_delta" and block.get("type") == "tool_use":
        partial_json = _read_optional_string(delta.get("partial_json"))
        if partial_json is None:
            return
        state.input_json_by_index[index] = f"{state.input_json_by_index.get(index, '')}{partial_json}"


def _build_anthropic_content_blocks(
    state: AnthropicSynthesisState,
) -> list[dict[str, Any]]:
    content_blocks: list[dict[str, Any]] = []
    for index in sorted(state.blocks_by_index):
        block = dict(state.blocks_by_index[index])
        if block.get("type") == "tool_use":
            accumulated_input = state.input_json_by_index.get(index)
            if accumulated_input:
                block["input"] = accumulated_input
        content_blocks.append(block)
    return content_blocks


def _read_content_block_index(value: Any) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None


def _read_optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None
