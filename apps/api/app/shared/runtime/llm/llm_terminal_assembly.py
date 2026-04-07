from __future__ import annotations

from ..errors import ConfigurationError
from .llm_protocol_types import NormalizedLLMResponse, normalize_api_dialect


def build_stream_completion(
    *,
    api_dialect: str,
    text_parts: list[str],
    terminal_response: NormalizedLLMResponse | None,
) -> NormalizedLLMResponse | None:
    delta_content = "".join(text_parts).strip()
    if terminal_response is None:
        return _build_delta_only_completion(delta_content)
    terminal_content = terminal_response.content.strip()
    content = _resolve_stream_content(
        api_dialect=api_dialect,
        delta_content=delta_content,
        terminal_content=terminal_content,
    )
    if not content and not terminal_response.tool_calls:
        return None
    return NormalizedLLMResponse(
        content=content,
        finish_reason=terminal_response.finish_reason,
        input_tokens=terminal_response.input_tokens,
        output_tokens=terminal_response.output_tokens,
        total_tokens=terminal_response.total_tokens,
        tool_calls=list(terminal_response.tool_calls),
        provider_response_id=terminal_response.provider_response_id,
        provider_output_items=list(terminal_response.provider_output_items),
    )


def _build_delta_only_completion(delta_content: str) -> NormalizedLLMResponse | None:
    if not delta_content:
        return None
    return NormalizedLLMResponse(
        content=delta_content,
        finish_reason=None,
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
    )


def _resolve_stream_content(
    *,
    api_dialect: str,
    delta_content: str,
    terminal_content: str,
) -> str:
    if not delta_content:
        return terminal_content
    if not terminal_content:
        return delta_content
    if delta_content == terminal_content:
        return terminal_content
    dialect = normalize_api_dialect(api_dialect)
    if dialect == "openai_responses":
        raise ConfigurationError(
            f"流式终态文本与已累计的增量文本不一致（api_dialect={dialect}）"
        )
    return delta_content
