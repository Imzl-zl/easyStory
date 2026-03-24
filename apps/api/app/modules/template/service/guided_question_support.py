from __future__ import annotations

LEGACY_GUIDED_QUESTION_VARIABLE_ALIASES = {
    "conflict": "core_conflict",
}


def normalize_guided_question_text(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty")
    return normalized


def normalize_guided_question_variable(value: str) -> str:
    normalized = normalize_guided_question_text(value, field_name="variable")
    return LEGACY_GUIDED_QUESTION_VARIABLE_ALIASES.get(normalized, normalized)
