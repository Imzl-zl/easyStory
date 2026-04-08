from __future__ import annotations

from app.shared.runtime.llm.interop.tool_schema_compiler import compile_tool_parameters


def test_compile_tool_parameters_simplifies_required_only_anyof_for_portable_subset() -> None:
    schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 1},
            "path_prefix": {"type": "string", "minLength": 1},
        },
        "anyOf": [
            {"required": ["query"]},
            {"required": ["path_prefix"]},
        ],
    }

    compiled = compile_tool_parameters(schema, mode="portable_subset")

    assert compiled == {
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 1},
            "path_prefix": {"type": "string", "minLength": 1},
        },
        "description": "Provide at least one of: path_prefix, query.",
    }
    assert "anyOf" in schema


def test_compile_tool_parameters_keeps_non_required_only_anyof() -> None:
    schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "path_prefix": {"type": "string"},
        },
        "anyOf": [
            {"properties": {"query": {"type": "string"}}},
            {"required": ["path_prefix"]},
        ],
    }

    compiled = compile_tool_parameters(schema, mode="portable_subset")

    assert compiled == schema


def test_compile_tool_parameters_strips_gemini_incompatible_keys_recursively() -> None:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "paths": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
            },
            "options": {
                "type": "object",
                "additionalProperties": False,
                "properties": {"mode": {"type": "string"}},
                "required": ["mode"],
            },
        },
        "required": ["paths"],
    }

    compiled = compile_tool_parameters(schema, mode="gemini_compatible")

    assert compiled == {
        "type": "object",
        "properties": {
            "paths": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
            },
            "options": {
                "type": "object",
                "properties": {"mode": {"type": "string"}},
                "required": ["mode"],
            },
        },
        "required": ["paths"],
    }
    assert schema["additionalProperties"] is False


def test_compile_tool_parameters_merges_required_note_with_existing_description_once() -> None:
    schema = {
        "type": "object",
        "description": "检索文稿。",
        "properties": {
            "query": {"type": "string"},
            "path_prefix": {"type": "string"},
        },
        "anyOf": [
            {"required": ["query"]},
            {"required": ["path_prefix"]},
        ],
    }

    compiled = compile_tool_parameters(schema, mode="portable_subset")

    assert compiled["description"] == "检索文稿。 Provide at least one of: path_prefix, query."
