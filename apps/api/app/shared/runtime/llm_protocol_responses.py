from __future__ import annotations

from typing import Any

from .errors import ConfigurationError
from .llm_protocol_types import NormalizedLLMResponse, normalize_api_dialect


def parse_generation_response(
    api_dialect: str,
    payload: dict[str, Any],
) -> NormalizedLLMResponse:
    dialect = normalize_api_dialect(api_dialect)
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
    usage = _require_dict(payload.get("usage"), "usage", allow_none=True) or {}
    return _build_normalized_response(content, usage, "prompt_tokens", "completion_tokens", "total_tokens")


def _parse_openai_responses_response(payload: dict[str, Any]) -> NormalizedLLMResponse:
    output_text = payload.get("output_text")
    if isinstance(output_text, str):
        content = output_text
    else:
        content = _extract_responses_text(payload)
    usage = _require_dict(payload.get("usage"), "usage", allow_none=True) or {}
    return _build_normalized_response(content, usage, "input_tokens", "output_tokens", "total_tokens")


def _parse_anthropic_messages_response(payload: dict[str, Any]) -> NormalizedLLMResponse:
    blocks = _require_list(payload.get("content"), "content")
    content = "".join(
        block.get("text", "")
        for block in blocks
        if isinstance(block, dict) and isinstance(block.get("text"), str)
    )
    usage = _require_dict(payload.get("usage"), "usage", allow_none=True) or {}
    return _build_normalized_response(content, usage, "input_tokens", "output_tokens", None)


def _parse_gemini_generate_content_response(payload: dict[str, Any]) -> NormalizedLLMResponse:
    candidates = _require_list(payload.get("candidates"), "candidates")
    first_candidate = _require_dict(candidates[0], "candidates[0]")
    content = _require_dict(first_candidate.get("content"), "candidates[0].content")
    parts = _require_list(content.get("parts"), "candidates[0].content.parts")
    text = "".join(
        part.get("text", "")
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    )
    usage = _require_dict(payload.get("usageMetadata"), "usageMetadata", allow_none=True) or {}
    return _build_normalized_response(
        text,
        usage,
        "promptTokenCount",
        "candidatesTokenCount",
        "totalTokenCount",
    )


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


def _build_normalized_response(
    content: str,
    usage: dict[str, Any],
    input_key: str,
    output_key: str,
    total_key: str | None,
) -> NormalizedLLMResponse:
    input_tokens = _optional_int(usage.get(input_key))
    output_tokens = _optional_int(usage.get(output_key))
    total_tokens = _optional_int(usage.get(total_key)) if total_key else None
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    return NormalizedLLMResponse(
        content=content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


def _stringify_openai_content(content: Any) -> str:
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
