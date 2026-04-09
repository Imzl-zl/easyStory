from __future__ import annotations

from .llm_protocol_types import GeminiThinkingLevel, LlmApiDialect, OpenAIReasoningEffort

OPENAI_REASONING_FIELD = "reasoning_effort"
GEMINI_THINKING_LEVEL_FIELD = "thinking_level"
GEMINI_THINKING_BUDGET_FIELD = "thinking_budget"
OPENAI_REASONING_DIALECTS = frozenset({"openai_chat_completions", "openai_responses"})


def build_provider_native_reasoning_error(
    *,
    provider: str | None,
    api_dialect: LlmApiDialect | None = None,
    reasoning_effort: OpenAIReasoningEffort | None,
    thinking_level: GeminiThinkingLevel | None,
    thinking_budget: int | None,
    field_prefix: str = "",
) -> str | None:
    shape_error = build_provider_native_reasoning_shape_error(
        reasoning_effort=reasoning_effort,
        thinking_level=thinking_level,
        thinking_budget=thinking_budget,
        field_prefix=field_prefix,
    )
    if shape_error is not None:
        return shape_error
    reasoning_field = _field_name(field_prefix, OPENAI_REASONING_FIELD)
    thinking_level_field = _field_name(field_prefix, GEMINI_THINKING_LEVEL_FIELD)
    thinking_budget_field = _field_name(field_prefix, GEMINI_THINKING_BUDGET_FIELD)
    normalized_provider = _normalize_optional_text(provider)
    if api_dialect is not None:
        return _build_api_dialect_reasoning_error(
            api_dialect=api_dialect,
            reasoning_effort=reasoning_effort,
            thinking_level=thinking_level,
            thinking_budget=thinking_budget,
            reasoning_field=reasoning_field,
            thinking_level_field=thinking_level_field,
            thinking_budget_field=thinking_budget_field,
        )
    provider_family = _infer_provider_family(normalized_provider)
    if provider_family is None:
        return None
    return _build_family_reasoning_error(
        family=provider_family,
        reasoning_effort=reasoning_effort,
        thinking_level=thinking_level,
        thinking_budget=thinking_budget,
        reasoning_field=reasoning_field,
        thinking_level_field=thinking_level_field,
        thinking_budget_field=thinking_budget_field,
    )


def build_provider_native_reasoning_shape_error(
    *,
    reasoning_effort: OpenAIReasoningEffort | None,
    thinking_level: GeminiThinkingLevel | None,
    thinking_budget: int | None,
    field_prefix: str = "",
) -> str | None:
    reasoning_field = _field_name(field_prefix, OPENAI_REASONING_FIELD)
    thinking_level_field = _field_name(field_prefix, GEMINI_THINKING_LEVEL_FIELD)
    thinking_budget_field = _field_name(field_prefix, GEMINI_THINKING_BUDGET_FIELD)
    if thinking_level is not None and thinking_budget is not None:
        return f"{thinking_level_field} and {thinking_budget_field} cannot both be set"
    if reasoning_effort is not None and (thinking_level is not None or thinking_budget is not None):
        return (
            f"{reasoning_field} cannot be combined with "
            f"{thinking_level_field} or {thinking_budget_field}"
        )
    return None


def _build_api_dialect_reasoning_error(
    *,
    api_dialect: LlmApiDialect,
    reasoning_effort: OpenAIReasoningEffort | None,
    thinking_level: GeminiThinkingLevel | None,
    thinking_budget: int | None,
    reasoning_field: str,
    thinking_level_field: str,
    thinking_budget_field: str,
) -> str | None:
    if api_dialect in OPENAI_REASONING_DIALECTS:
        return _build_family_reasoning_error(
            family="openai",
            reasoning_effort=reasoning_effort,
            thinking_level=thinking_level,
            thinking_budget=thinking_budget,
            reasoning_field=reasoning_field,
            thinking_level_field=thinking_level_field,
            thinking_budget_field=thinking_budget_field,
        )
    if api_dialect == "gemini_generate_content":
        return _build_family_reasoning_error(
            family="gemini",
            reasoning_effort=reasoning_effort,
            thinking_level=thinking_level,
            thinking_budget=thinking_budget,
            reasoning_field=reasoning_field,
            thinking_level_field=thinking_level_field,
            thinking_budget_field=thinking_budget_field,
        )
    if reasoning_effort is not None:
        return f"{reasoning_field} is not valid for {api_dialect} requests"
    if thinking_level is not None or thinking_budget is not None:
        return (
            f"{thinking_level_field} and {thinking_budget_field} are only valid for "
            "Gemini native requests"
        )
    return None


def _build_family_reasoning_error(
    *,
    family: str,
    reasoning_effort: OpenAIReasoningEffort | None,
    thinking_level: GeminiThinkingLevel | None,
    thinking_budget: int | None,
    reasoning_field: str,
    thinking_level_field: str,
    thinking_budget_field: str,
) -> str | None:
    if family == "openai":
        if thinking_level is not None or thinking_budget is not None:
            return (
                f"{thinking_level_field} and {thinking_budget_field} are only valid for "
                "Gemini native requests"
            )
        return None
    if family == "gemini":
        if reasoning_effort is not None:
            return f"{reasoning_field} is not valid for Gemini native requests"
        return None
    if family == "anthropic":
        if reasoning_effort is not None:
            return f"{reasoning_field} is not valid for Anthropic requests"
        if thinking_level is not None or thinking_budget is not None:
            return (
                f"{thinking_level_field} and {thinking_budget_field} are only valid for "
                "Gemini native requests"
            )
    return None


def _infer_provider_family(provider: str | None) -> str | None:
    if provider in {"openai", "gemini", "anthropic"}:
        return provider
    return None


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def _field_name(prefix: str, field_name: str) -> str:
    return f"{prefix}{field_name}" if prefix else field_name


__all__ = [
    "GEMINI_THINKING_BUDGET_FIELD",
    "GEMINI_THINKING_LEVEL_FIELD",
    "OPENAI_REASONING_FIELD",
    "build_provider_native_reasoning_error",
    "build_provider_native_reasoning_shape_error",
]
