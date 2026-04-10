from __future__ import annotations

from typing import Any, Literal, cast

ToolSchemaMode = Literal["openai_strict_compatible", "portable_subset", "gemini_compatible"]

TOOL_SCHEMA_REQUIRED_NOTE_PREFIX = "Provide at least one of:"
GEMINI_UNSUPPORTED_SCHEMA_KEYS = frozenset({"additionalProperties"})
NULL_SCHEMA_TYPE = "null"


def compile_tool_parameters(
    schema: dict[str, Any],
    *,
    mode: ToolSchemaMode,
) -> dict[str, Any]:
    compiled = _compile_schema_value(schema, mode=mode)
    if mode == "openai_strict_compatible":
        compiled = _normalize_openai_strict_schema(compiled)
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
    # This is an intentional portability downgrade: preserve the "at least one of"
    # constraint as description text, while emitting a schema subset that current
    # strict tool gateways accept consistently.
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


def _normalize_openai_strict_schema(value: Any) -> Any:
    if isinstance(value, list):
        return [_normalize_openai_strict_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    normalized = {
        key: _normalize_openai_strict_schema(item)
        for key, item in value.items()
    }
    normalized = _collapse_nullable_anyof_schema(normalized)
    if normalized.get("type") != "object":
        return normalized
    properties = normalized.get("properties")
    if not isinstance(properties, dict):
        return normalized
    property_names = list(properties.keys())
    required = _read_required_property_names(normalized.get("required"))
    # OpenAI strict requires every declared property to appear in required; optional
    # fields are represented as nullable instead of being omitted from required.
    normalized["properties"] = {
        name: (
            properties[name]
            if name in required
            else _make_schema_nullable(cast(dict[str, Any], properties[name]))
        )
        for name in property_names
    }
    normalized["required"] = property_names
    return normalized


def _collapse_nullable_anyof_schema(schema: dict[str, Any]) -> dict[str, Any]:
    any_of = schema.get("anyOf")
    if not isinstance(any_of, list):
        return schema
    non_null_entries = [
        item
        for item in any_of
        if not (isinstance(item, dict) and item.get("type") == NULL_SCHEMA_TYPE)
    ]
    if len(non_null_entries) != 1 or len(non_null_entries) == len(any_of):
        return schema
    nullable_branch = non_null_entries[0]
    if not isinstance(nullable_branch, dict):
        return schema
    collapsed = {
        key: value
        for key, value in schema.items()
        if key != "anyOf"
    }
    for key, value in nullable_branch.items():
        collapsed.setdefault(key, value)
    return _make_schema_nullable(collapsed)


def _read_required_property_names(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    names = {item for item in value if isinstance(item, str) and item.strip()}
    return names


def _make_schema_nullable(schema: dict[str, Any]) -> dict[str, Any]:
    if _schema_is_nullable(schema):
        return schema
    nullable = dict(schema)
    schema_type = nullable.get("type")
    if isinstance(schema_type, str):
        nullable["type"] = [schema_type, NULL_SCHEMA_TYPE]
    elif isinstance(schema_type, list):
        nullable["type"] = [*schema_type, NULL_SCHEMA_TYPE]
    else:
        any_of = nullable.get("anyOf")
        if isinstance(any_of, list):
            nullable["anyOf"] = [*any_of, {"type": NULL_SCHEMA_TYPE}]
        else:
            nullable["anyOf"] = [schema, {"type": NULL_SCHEMA_TYPE}]
    enum_values = _append_enum_null(nullable.get("enum"))
    if enum_values is not None:
        nullable["enum"] = enum_values
    return nullable


def _schema_is_nullable(schema: dict[str, Any]) -> bool:
    schema_type = schema.get("type")
    if schema_type == NULL_SCHEMA_TYPE:
        return True
    if isinstance(schema_type, list) and NULL_SCHEMA_TYPE in schema_type:
        return True
    any_of = schema.get("anyOf")
    if not isinstance(any_of, list):
        return False
    return any(
        isinstance(item, dict) and item.get("type") == NULL_SCHEMA_TYPE
        for item in any_of
    )


def _append_enum_null(value: Any) -> Any:
    if not isinstance(value, list):
        return None
    if None in value:
        return value
    return [*value, None]
