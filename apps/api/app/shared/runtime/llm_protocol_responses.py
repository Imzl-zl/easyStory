from __future__ import annotations

import json
from typing import Any

from .errors import ConfigurationError
from .llm_protocol_types import NormalizedLLMResponse, NormalizedLLMToolCall, normalize_api_dialect

TRUNCATED_STOP_REASONS = frozenset({"length", "max_tokens", "max_output_tokens", "MAX_TOKENS"})


def parse_generation_response(
    api_dialect: str,
    payload: dict[str, Any],
) -> NormalizedLLMResponse:
    dialect = normalize_api_dialect(api_dialect)
    _raise_if_response_truncated(dialect, payload)
    if dialect == "openai_chat_completions":
        return _parse_openai_chat_response(payload)
    if dialect == "openai_responses":
        return _parse_openai_responses_response(payload)
    if dialect == "anthropic_messages":
        return _parse_anthropic_messages_response(payload)
    return _parse_gemini_generate_content_response(payload)


def _parse_openai_chat_response(payload: dict[str, Any]) -> NormalizedLLMResponse:
    choices = _require_list(payload.get("choices"), "choices")
    first_choice = _require_dict(choices[0], "choices[0]")
    message = _require_dict(first_choice.get("message"), "choices[0].message")
    content = _stringify_openai_content(message.get("content"))
    tool_calls = _extract_openai_chat_tool_calls(message)
    usage = _require_dict(payload.get("usage"), "usage", allow_none=True) or {}
    return _build_normalized_response(
        content,
        usage,
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        finish_reason=_extract_openai_chat_stop_reason(payload),
        tool_calls=tool_calls,
        provider_output_items=_build_openai_chat_output_items(message),
    )


def _parse_openai_responses_response(payload: dict[str, Any]) -> NormalizedLLMResponse:
    output_text = payload.get("output_text")
    if isinstance(output_text, str):
        content = output_text
    else:
        content = _extract_responses_text(payload)
    tool_calls = _extract_openai_responses_tool_calls(payload)
    usage = _require_dict(payload.get("usage"), "usage", allow_none=True) or {}
    return _build_normalized_response(
        content,
        usage,
        "input_tokens",
        "output_tokens",
        "total_tokens",
        finish_reason=_extract_openai_responses_stop_reason(payload),
        tool_calls=tool_calls,
        provider_response_id=_optional_string(payload.get("id")),
        provider_output_items=_build_openai_responses_output_items(payload),
    )


def _parse_anthropic_messages_response(payload: dict[str, Any]) -> NormalizedLLMResponse:
    blocks = _require_list(payload.get("content"), "content")
    content = "".join(
        block.get("text", "")
        for block in blocks
        if isinstance(block, dict) and isinstance(block.get("text"), str)
    )
    tool_calls = _extract_anthropic_tool_calls(blocks)
    usage = _require_dict(payload.get("usage"), "usage", allow_none=True) or {}
    return _build_normalized_response(
        content,
        usage,
        "input_tokens",
        "output_tokens",
        None,
        finish_reason=_extract_anthropic_stop_reason(payload),
        tool_calls=tool_calls,
        provider_response_id=_optional_string(payload.get("id")),
    )


def _parse_gemini_generate_content_response(payload: dict[str, Any]) -> NormalizedLLMResponse:
    candidates = _require_list(payload.get("candidates"), "candidates")
    first_candidate = _require_dict(candidates[0], "candidates[0]")
    content = _require_dict(first_candidate.get("content"), "candidates[0].content")
    parts = _require_list(content.get("parts"), "candidates[0].content.parts", allow_none=True)
    if parts is None:
        raise ConfigurationError(_build_gemini_empty_content_message(first_candidate))
    text = "".join(
        part.get("text", "")
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    )
    tool_calls = _extract_gemini_tool_calls(parts)
    usage = _require_dict(payload.get("usageMetadata"), "usageMetadata", allow_none=True) or {}
    return _build_normalized_response(
        text,
        usage,
        "promptTokenCount",
        "candidatesTokenCount",
        "totalTokenCount",
        finish_reason=_extract_gemini_stop_reason(payload),
        tool_calls=tool_calls,
    )


def _raise_if_response_truncated(
    api_dialect: str,
    payload: dict[str, Any],
) -> None:
    stop_reason = _extract_stop_reason(api_dialect, payload)
    if stop_reason not in TRUNCATED_STOP_REASONS:
        return
    raise ConfigurationError(
        "上游在输出尚未完成时提前停止了这次回复，"
        f"当前只收到部分内容（stop_reason={stop_reason}）。"
        "请在“模型与连接”里调高单次回复上限，或切换更稳定的连接后重试。"
    )


def _extract_stop_reason(api_dialect: str, payload: dict[str, Any]) -> str | None:
    if api_dialect == "openai_chat_completions":
        return _extract_openai_chat_stop_reason(payload)
    if api_dialect == "openai_responses":
        return _extract_openai_responses_stop_reason(payload)
    if api_dialect == "anthropic_messages":
        return _extract_anthropic_stop_reason(payload)
    return _extract_gemini_stop_reason(payload)


def _build_gemini_empty_content_message(candidate: dict[str, Any]) -> str:
    finish_reason = candidate.get("finishReason")
    if isinstance(finish_reason, str) and finish_reason:
        return (
            "Gemini response did not return text parts "
            f"(finishReason={finish_reason})"
        )
    return "candidates[0].content.parts must be a non-empty list"


def _extract_responses_text(payload: dict[str, Any]) -> str:
    output = _require_list(payload.get("output"), "output")
    parts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content = _require_list(item.get("content"), "output.content", allow_none=True) or []
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
    return "".join(parts)


def _extract_openai_chat_stop_reason(payload: dict[str, Any]) -> str | None:
    choices = _require_list(payload.get("choices"), "choices")
    first_choice = _require_dict(choices[0], "choices[0]")
    finish_reason = first_choice.get("finish_reason")
    return finish_reason if isinstance(finish_reason, str) else None


def _extract_openai_responses_stop_reason(payload: dict[str, Any]) -> str | None:
    incomplete_details = _require_dict(
        payload.get("incomplete_details"),
        "incomplete_details",
        allow_none=True,
    ) or {}
    reason = incomplete_details.get("reason")
    if isinstance(reason, str):
        return reason
    return None


def _extract_anthropic_stop_reason(payload: dict[str, Any]) -> str | None:
    stop_reason = payload.get("stop_reason")
    return stop_reason if isinstance(stop_reason, str) else None


def _extract_gemini_stop_reason(payload: dict[str, Any]) -> str | None:
    candidates = _require_list(payload.get("candidates"), "candidates")
    first_candidate = _require_dict(candidates[0], "candidates[0]")
    finish_reason = first_candidate.get("finishReason")
    return finish_reason if isinstance(finish_reason, str) else None


def _build_normalized_response(
    content: str,
    usage: dict[str, Any],
    input_key: str,
    output_key: str,
    total_key: str | None,
    *,
    finish_reason: str | None,
    tool_calls: list[NormalizedLLMToolCall] | None = None,
    provider_response_id: str | None = None,
    provider_output_items: list[dict[str, Any]] | None = None,
) -> NormalizedLLMResponse:
    input_tokens = _optional_int(usage.get(input_key))
    output_tokens = _optional_int(usage.get(output_key))
    total_tokens = _optional_int(usage.get(total_key)) if total_key else None
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    return NormalizedLLMResponse(
        content=content,
        finish_reason=finish_reason,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        tool_calls=list(tool_calls or []),
        provider_response_id=provider_response_id,
        provider_output_items=list(provider_output_items or []),
    )


def _stringify_openai_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict)
        )
    raise ConfigurationError("OpenAI chat response content must be string or list")


def _require_list(value: Any, field_name: str, *, allow_none: bool = False) -> list[Any] | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, list) or not value:
        raise ConfigurationError(f"{field_name} must be a non-empty list")
    return value


def _require_dict(value: Any, field_name: str, *, allow_none: bool = False) -> dict[str, Any] | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, dict):
        raise ConfigurationError(f"{field_name} must be an object")
    return value


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError("Expected integer value")
    return value


def _optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _extract_openai_chat_tool_calls(message: dict[str, Any]) -> list[NormalizedLLMToolCall]:
    tool_calls = _require_list(message.get("tool_calls"), "message.tool_calls", allow_none=True) or []
    items: list[NormalizedLLMToolCall] = []
    for item in tool_calls:
        if not isinstance(item, dict):
            continue
        function = _require_dict(item.get("function"), "message.tool_calls.function", allow_none=True) or {}
        items.append(
            _build_tool_call(
                tool_call_id=_optional_string(item.get("id")),
                tool_name=_optional_string(function.get("name")),
                arguments=_parse_tool_arguments(function.get("arguments")),
            )
        )
    return items


def _build_openai_chat_output_items(message: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    content = _stringify_openai_content(message.get("content"))
    if content.strip():
        items.append(
            {
                "item_type": "text",
                "item_id": "provider:openai_chat:text:0",
                "status": "completed",
                "payload": {"content": content, "phase": "final"},
            }
        )
    for index, tool_call in enumerate(_extract_openai_chat_tool_calls(message), start=1):
        items.append(
            {
                "item_type": "tool_call",
                "item_id": f"provider:openai_chat:tool_call:{index}",
                "status": "completed",
                "provider_ref": tool_call.provider_ref,
                "call_id": tool_call.tool_call_id,
                "payload": {
                    "tool_name": tool_call.tool_name,
                    "arguments": tool_call.arguments,
                    "arguments_text": tool_call.arguments_text,
                    "tool_call_id": tool_call.tool_call_id,
                },
            }
        )
    return items


def _extract_openai_responses_tool_calls(payload: dict[str, Any]) -> list[NormalizedLLMToolCall]:
    output = _require_list(payload.get("output"), "output", allow_none=True) or []
    items: list[NormalizedLLMToolCall] = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "function_call":
            continue
        items.append(
            _build_tool_call(
                tool_call_id=_optional_string(item.get("call_id")) or _optional_string(item.get("id")),
                tool_name=_optional_string(item.get("name")),
                arguments=_parse_tool_arguments(item.get("arguments")),
                provider_ref=_optional_string(item.get("id")),
            )
        )
    return items


def _build_openai_responses_output_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    output = _require_list(payload.get("output"), "output", allow_none=True)
    items: list[dict[str, Any]] = []
    text_index = 0
    tool_call_index = 0
    reasoning_index = 0
    refusal_index = 0
    if output is None:
        output_text = payload.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return [
                {
                    "item_type": "text",
                    "item_id": "provider:openai_responses:text:1",
                    "status": "completed",
                    "provider_ref": _optional_string(payload.get("id")),
                    "payload": {"content": output_text, "phase": "final"},
                }
            ]
        return []
    for item in output:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        provider_ref = _optional_string(item.get("id"))
        if item_type == "function_call":
            tool_call_index += 1
            arguments, arguments_text = _parse_tool_arguments(item.get("arguments"))
            call_id = _optional_string(item.get("call_id")) or provider_ref
            if call_id is None:
                continue
            items.append(
                {
                    "item_type": "tool_call",
                    "item_id": f"provider:openai_responses:tool_call:{tool_call_index}",
                    "status": "completed",
                    "provider_ref": provider_ref,
                    "call_id": call_id,
                    "payload": {
                        "tool_name": _optional_string(item.get("name")),
                        "arguments": arguments,
                        "arguments_text": arguments_text,
                        "tool_call_id": call_id,
                    },
                }
            )
            continue
        if item_type == "reasoning":
            reasoning_index += 1
            items.append(
                {
                    "item_type": "reasoning",
                    "item_id": f"provider:openai_responses:reasoning:{reasoning_index}",
                    "status": _optional_string(item.get("status")) or "completed",
                    "provider_ref": provider_ref,
                    "payload": item,
                }
            )
            continue
        if item_type == "refusal":
            refusal_index += 1
            items.append(
                {
                    "item_type": "refusal",
                    "item_id": f"provider:openai_responses:refusal:{refusal_index}",
                    "status": _optional_string(item.get("status")) or "completed",
                    "provider_ref": provider_ref,
                    "payload": item,
                }
            )
            continue
        content = _require_list(item.get("content"), "output.content", allow_none=True) or []
        for block in content:
            if not isinstance(block, dict):
                continue
            text = block.get("text")
            if not isinstance(text, str) or not text.strip():
                continue
            text_index += 1
            items.append(
                {
                    "item_type": "text",
                    "item_id": f"provider:openai_responses:text:{text_index}",
                    "status": "completed",
                    "provider_ref": provider_ref,
                    "payload": {"content": text, "phase": "final"},
                }
            )
    return items


def _extract_anthropic_tool_calls(blocks: list[Any]) -> list[NormalizedLLMToolCall]:
    items: list[NormalizedLLMToolCall] = []
    for block in blocks:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        items.append(
            _build_tool_call(
                tool_call_id=_optional_string(block.get("id")),
                tool_name=_optional_string(block.get("name")),
                arguments=_parse_tool_arguments(block.get("input")),
            )
        )
    return items


def _extract_gemini_tool_calls(parts: list[Any]) -> list[NormalizedLLMToolCall]:
    items: list[NormalizedLLMToolCall] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        function_call = _require_dict(part.get("functionCall"), "part.functionCall", allow_none=True)
        if function_call is None:
            continue
        items.append(
            _build_tool_call(
                tool_call_id=_optional_string(function_call.get("id")),
                tool_name=_optional_string(function_call.get("name")),
                arguments=_parse_tool_arguments(function_call.get("args")),
            )
        )
    return items


def _build_tool_call(
    *,
    tool_call_id: str | None,
    tool_name: str | None,
    arguments: tuple[dict[str, Any] | None, str | None],
    provider_ref: str | None = None,
) -> NormalizedLLMToolCall:
    if tool_call_id is None:
        raise ConfigurationError("Tool call is missing id")
    if tool_name is None:
        raise ConfigurationError("Tool call is missing name")
    parsed_arguments, arguments_text = arguments
    return NormalizedLLMToolCall(
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        arguments=parsed_arguments,
        arguments_text=arguments_text,
        provider_ref=provider_ref,
    )


def _parse_tool_arguments(value: Any) -> tuple[dict[str, Any] | None, str | None]:
    if isinstance(value, dict):
        return value, json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    if value is None:
        return None, None
    if not isinstance(value, str):
        raise ConfigurationError("Tool call arguments must be an object or JSON string")
    text = value.strip()
    if not text:
        return None, None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigurationError("Tool call arguments JSON is invalid") from exc
    if not isinstance(parsed, dict):
        raise ConfigurationError("Tool call arguments JSON must decode to an object")
    return parsed, text
