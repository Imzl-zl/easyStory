from __future__ import annotations

import json
from typing import Any

from ...errors import ConfigurationError
from ..llm_protocol_types import NormalizedLLMToolCall
from .codec_value_helpers import (
    optional_string as _optional_string,
    require_dict as _require_dict,
    require_list as _require_list,
)
from .tool_name_codec import decode_tool_name


def extract_openai_chat_tool_calls(
    message: dict[str, Any],
    *,
    tool_name_aliases: dict[str, str],
) -> list[NormalizedLLMToolCall]:
    tool_calls = _require_list(message.get("tool_calls"), "message.tool_calls", allow_none=True) or []
    items: list[NormalizedLLMToolCall] = []
    for item in tool_calls:
        if not isinstance(item, dict):
            continue
        function = _require_dict(item.get("function"), "message.tool_calls.function", allow_none=True) or {}
        items.append(
            build_tool_call(
                tool_call_id=_optional_string(item.get("id")),
                tool_name=resolve_tool_name(
                    _optional_string(function.get("name")),
                    tool_name_aliases=tool_name_aliases,
                ),
                arguments=parse_tool_arguments(function.get("arguments")),
            )
        )
    return items


def extract_openai_responses_tool_calls(
    output: list[Any],
    *,
    tool_name_aliases: dict[str, str],
) -> list[NormalizedLLMToolCall]:
    items: list[NormalizedLLMToolCall] = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "function_call":
            continue
        items.append(
            build_tool_call(
                tool_call_id=_optional_string(item.get("call_id")) or _optional_string(item.get("id")),
                tool_name=resolve_tool_name(
                    _optional_string(item.get("name")),
                    tool_name_aliases=tool_name_aliases,
                ),
                arguments=parse_tool_arguments(item.get("arguments")),
                provider_ref=_optional_string(item.get("id")),
            )
        )
    return items


def extract_anthropic_tool_calls(
    blocks: list[Any],
    *,
    tool_name_aliases: dict[str, str],
) -> list[NormalizedLLMToolCall]:
    items: list[NormalizedLLMToolCall] = []
    for block in blocks:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        items.append(
            build_tool_call(
                tool_call_id=_optional_string(block.get("id")),
                tool_name=resolve_tool_name(
                    _optional_string(block.get("name")),
                    tool_name_aliases=tool_name_aliases,
                ),
                arguments=parse_tool_arguments(block.get("input")),
            )
        )
    return items


def extract_gemini_tool_calls(
    parts: list[Any],
    *,
    tool_name_aliases: dict[str, str],
) -> list[NormalizedLLMToolCall]:
    items: list[NormalizedLLMToolCall] = []
    for index, part in enumerate(parts, start=1):
        if not isinstance(part, dict):
            continue
        function_call = _require_dict(part.get("functionCall"), "part.functionCall", allow_none=True)
        if function_call is None:
            continue
        items.append(
            build_tool_call(
                tool_call_id=(
                    _optional_string(function_call.get("id"))
                    or f"provider:gemini_generate_content:tool_call:{index}"
                ),
                tool_name=resolve_tool_name(
                    _optional_string(function_call.get("name")),
                    tool_name_aliases=tool_name_aliases,
                ),
                arguments=parse_tool_arguments(function_call.get("args")),
                provider_payload=_copy_provider_payload(part),
            )
        )
    return items


def build_tool_call(
    *,
    tool_call_id: str | None,
    tool_name: str | None,
    arguments: tuple[dict[str, Any], str | None, str | None],
    provider_ref: str | None = None,
    provider_payload: dict[str, Any] | None = None,
) -> NormalizedLLMToolCall:
    if tool_call_id is None:
        raise ConfigurationError("Tool call is missing id")
    if tool_name is None:
        raise ConfigurationError("Tool call is missing name")
    parsed_arguments, arguments_text, arguments_error = arguments
    return NormalizedLLMToolCall(
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        arguments=parsed_arguments,
        arguments_text=arguments_text,
        arguments_error=arguments_error,
        provider_ref=provider_ref,
        provider_payload=provider_payload,
    )


def resolve_tool_name(
    tool_name: str | None,
    *,
    tool_name_aliases: dict[str, str],
) -> str | None:
    if tool_name is None:
        return None
    return decode_tool_name(
        tool_name,
        tool_name_aliases=tool_name_aliases,
    )


def parse_tool_arguments(value: Any) -> tuple[dict[str, Any], str | None, str | None]:
    if isinstance(value, dict):
        return (
            value,
            json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
            None,
        )
    if value is None:
        return {}, None, None
    if not isinstance(value, str):
        return {}, None, "Tool call arguments must be an object or JSON string"
    text = value.strip()
    if not text:
        return {}, None, None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}, text, "Tool call arguments JSON is invalid"
    if not isinstance(parsed, dict):
        return {}, text, "Tool call arguments JSON must decode to an object"
    return parsed, text, None


def build_tool_call_payload(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    arguments_text: str | None,
    tool_call_id: str,
    arguments_error: str | None = None,
    provider_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "tool_name": tool_name,
        "arguments": arguments,
        "arguments_text": arguments_text,
        "tool_call_id": tool_call_id,
    }
    if arguments_error is not None:
        payload["arguments_error"] = arguments_error
    if provider_payload is not None:
        payload["provider_payload"] = provider_payload
    return payload


def _copy_provider_payload(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return dict(value)
