from __future__ import annotations

from typing import Any, Literal, cast

ToolSchemaMode = Literal["portable_subset", "gemini_compatible"]

TOOL_SCHEMA_REQUIRED_NOTE_PREFIX = "Provide at least one of:"
GEMINI_UNSUPPORTED_SCHEMA_KEYS = frozenset({"additionalProperties"})


def compile_tool_parameters(
    schema: dict[str, Any],
    *,
    mode: ToolSchemaMode,
) -> dict[str, Any]:
    compiled = _compile_schema_value(schema, mode=mode)
    return cast(dict[str, Any], compiled)


def _compile_schema_value(value: Any, *, mode: ToolSchemaMode) -> Any:
    if isinstance(value, dict):
        compiled = {
            key: _compile_schema_value(item, mode=mode)
            for key, item in value.items()
            if _should_keep_schema_key(key, mode=mode)
        }
        return _simplify_required_only_any_of(compiled)
    if isinstance(value, list):
        return [_compile_schema_value(item, mode=mode) for item in value]
    return value


def _should_keep_schema_key(key: str, *, mode: ToolSchemaMode) -> bool:
    if mode != "gemini_compatible":
        return True
    return key not in GEMINI_UNSUPPORTED_SCHEMA_KEYS


def _simplify_required_only_any_of(schema: dict[str, Any]) -> dict[str, Any]:
    any_of = schema.get("anyOf")
    if not _is_required_only_any_of(any_of):
        return schema
    required_fields = sorted({field for entry in any_of for field in entry["required"]})
    simplified = {key: value for key, value in schema.items() if key != "anyOf"}
    simplified["description"] = _merge_schema_description(
        simplified.get("description"),
        f"{TOOL_SCHEMA_REQUIRED_NOTE_PREFIX} {', '.join(required_fields)}.",
    )
    return simplified


def _is_required_only_any_of(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    for entry in value:
        if not isinstance(entry, dict):
            return False
        required = entry.get("required")
        if set(entry.keys()) != {"required"}:
            return False
        if not isinstance(required, list) or not required:
            return False
        if any(not isinstance(field, str) or not field.strip() for field in required):
            return False
    return True


def _merge_schema_description(existing: Any, note: str) -> str:
    if not isinstance(existing, str) or not existing.strip():
        return note
    if note in existing:
        return existing
    return f"{existing.strip()} {note}"
