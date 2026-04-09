from __future__ import annotations

from typing import Any

from ...errors import ConfigurationError
from ..llm_protocol_types import LLMGenerateRequest
from .tool_result_codec import (
    build_openai_responses_function_call_outputs as codec_build_openai_responses_function_call_outputs,
)


def build_openai_responses_input(
    request: LLMGenerateRequest,
    *,
    prompt_builder,
) -> list[dict[str, Any]]:
    previous_response_id = read_previous_response_id(request.provider_continuation_state)
    if previous_response_id is not None:
        # Responses continuation only accepts structured function_call_output items.
        # If latest_items cannot be projected into that shape, fail fast instead of
        # silently degrading to prompt replay.
        return _build_openai_responses_continuation_input(request)
    prompt = prompt_builder(request)
    return [
        {
            "role": "user",
            "content": [{"type": "input_text", "text": prompt}],
        }
    ]


def read_previous_response_id(state: dict[str, Any] | None) -> str | None:
    if not isinstance(state, dict):
        return None
    value = state.get("previous_response_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def read_latest_continuation_items(request: LLMGenerateRequest) -> list[dict[str, Any]]:
    state = request.provider_continuation_state
    if isinstance(state, dict):
        latest_items = state.get("latest_items")
        if isinstance(latest_items, list):
            return [item for item in latest_items if isinstance(item, dict)]
    return [item for item in request.continuation_items if isinstance(item, dict)]


def collect_continuation_tool_names(items: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        payload = item.get("payload")
        if item.get("item_type") == "tool_call" and isinstance(payload, dict):
            tool_name = payload.get("tool_name")
            if isinstance(tool_name, str) and tool_name.strip():
                names.append(tool_name.strip())
            continue
        if item.get("item_type") != "tool_result" or not isinstance(payload, dict):
            continue
        tool_name = item.get("tool_name")
        if isinstance(tool_name, str) and tool_name.strip():
            names.append(tool_name.strip())
            continue
        payload_tool_name = payload.get("tool_name")
        if isinstance(payload_tool_name, str) and payload_tool_name.strip():
            names.append(payload_tool_name.strip())
    return names


def _build_openai_responses_continuation_input(
    request: LLMGenerateRequest,
) -> list[dict[str, Any]]:
    continuation_items = read_latest_continuation_items(request)
    tool_outputs = codec_build_openai_responses_function_call_outputs(continuation_items)
    if tool_outputs:
        return tool_outputs
    raise ConfigurationError(
        "OpenAI responses continuation requires tool_result items with call_id and structured_output "
        "when previous_response_id is supplied"
    )
