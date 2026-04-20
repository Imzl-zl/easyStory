from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .codec_value_helpers import optional_string as _optional_string
from ..llm_protocol_types import NormalizedLLMResponse
from ..llm_protocol_responses import parse_generation_response


@dataclass
class OpenAIChatSynthesisState:
    tool_calls_by_index: dict[int, dict[str, Any]]
    finish_reason: str | None = None
    usage: dict[str, Any] | None = None
    response_id: str | None = None
    reasoning_content: str = ""


def synthesize_openai_chat_terminal_response(
    raw_events: list[tuple[str | None, dict[str, Any]]],
    *,
    tool_name_aliases: dict[str, str],
) -> NormalizedLLMResponse | None:
    state = OpenAIChatSynthesisState(tool_calls_by_index={})
    for _, payload in raw_events:
        _apply_openai_chat_event(state, payload)
    if not state.tool_calls_by_index:
        return None
    reconstructed_payload: dict[str, Any] = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        state.tool_calls_by_index[index] for index in sorted(state.tool_calls_by_index)
                    ],
                },
                "finish_reason": state.finish_reason or "tool_calls",
            }
        ]
    }
    if state.reasoning_content:
        reconstructed_payload["choices"][0]["message"]["reasoning_content"] = state.reasoning_content
    if state.usage is not None:
        reconstructed_payload["usage"] = state.usage
    if state.response_id is not None:
        reconstructed_payload["id"] = state.response_id
    return parse_generation_response(
        "openai_chat_completions",
        reconstructed_payload,
        tool_name_aliases=tool_name_aliases,
    )


def _apply_openai_chat_event(
    state: OpenAIChatSynthesisState,
    payload: dict[str, Any],
) -> None:
    if state.response_id is None:
        state.response_id = _optional_string(payload.get("id"))
    payload_usage = payload.get("usage")
    if isinstance(payload_usage, dict):
        state.usage = payload_usage
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return
    choice_finish_reason = _optional_string(first_choice.get("finish_reason"))
    if choice_finish_reason is not None:
        state.finish_reason = choice_finish_reason
    delta = first_choice.get("delta")
    if not isinstance(delta, dict):
        return
    reasoning_delta = _extract_openai_chat_reasoning_delta(delta)
    if reasoning_delta:
        state.reasoning_content += reasoning_delta
    tool_calls = delta.get("tool_calls")
    if not isinstance(tool_calls, list):
        return
    for fallback_index, item in enumerate(tool_calls):
        _merge_openai_chat_tool_call_delta(state, item, fallback_index=fallback_index)


def _merge_openai_chat_tool_call_delta(
    state: OpenAIChatSynthesisState,
    item: Any,
    *,
    fallback_index: int,
) -> None:
    if not isinstance(item, dict):
        return
    index = item.get("index")
    if not isinstance(index, int):
        index = fallback_index
    current = state.tool_calls_by_index.setdefault(
        index,
        {
            "id": None,
            "type": "function",
            "function": {
                "name": "",
                "arguments": "",
            },
        },
    )
    call_id = _optional_string(item.get("id"))
    if call_id is not None:
        current["id"] = call_id
    call_type = _optional_string(item.get("type"))
    if call_type is not None:
        current["type"] = call_type
    function = item.get("function")
    if not isinstance(function, dict):
        return
    name = _optional_string(function.get("name"))
    if name is not None:
        current["function"]["name"] = _merge_openai_chat_tool_name_delta(
            current["function"]["name"],
            name,
        )
    arguments_chunk = function.get("arguments")
    if isinstance(arguments_chunk, str):
        current["function"]["arguments"] += arguments_chunk


def _merge_openai_chat_tool_name_delta(previous_name: str, incoming_name: str) -> str:
    if not previous_name or previous_name.endswith(incoming_name):
        return incoming_name
    return f"{previous_name}{incoming_name}"


def _extract_openai_chat_reasoning_delta(delta: dict[str, Any]) -> str:
    reasoning_content = delta.get("reasoning_content")
    if isinstance(reasoning_content, str):
        return reasoning_content
    if not isinstance(reasoning_content, list):
        return ""
    return "".join(
        item.get("text", "")
        for item in reasoning_content
        if isinstance(item, dict) and isinstance(item.get("text"), str)
    )
