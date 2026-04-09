from __future__ import annotations

import pytest

from app.shared.runtime.llm.interop.tool_name_codec import (
    ToolNameAliasMap,
    build_tool_name_aliases,
    decode_tool_name,
)


def test_decode_tool_name_handles_safe_ascii_alias_collisions() -> None:
    aliases = build_tool_name_aliases(
        [
            "project.read_documents",
            "project_read_documents",
        ],
        policy="safe_ascii_only",
    )

    assert aliases["project.read_documents"] == "project_read_documents"
    assert aliases["project_read_documents"].startswith("project_read_documents__")
    assert decode_tool_name(
        aliases["project.read_documents"],
        tool_name_aliases=aliases,
    ) == "project.read_documents"
    assert decode_tool_name(
        aliases["project_read_documents"],
        tool_name_aliases=aliases,
    ) == "project_read_documents"


def test_decode_tool_name_keeps_unknown_tool_name() -> None:
    aliases = {"project.read_documents": "project_read_documents"}

    assert decode_tool_name(
        "project.search_documents",
        tool_name_aliases=aliases,
    ) == "project.search_documents"


def test_decode_tool_name_supports_plain_dict_alias_lookup() -> None:
    aliases = {"project.read_documents": "project_read_documents"}

    assert decode_tool_name(
        "project_read_documents",
        tool_name_aliases=aliases,
    ) == "project.read_documents"


def test_decode_tool_name_rebuilds_reverse_lookup_after_alias_map_mutation() -> None:
    aliases = build_tool_name_aliases(
        ["project.read_documents"],
        policy="safe_ascii_only",
    )

    aliases["project.search_documents"] = "project_search_documents"

    assert decode_tool_name(
        "project_search_documents",
        tool_name_aliases=aliases,
    ) == "project.search_documents"


def test_decode_tool_name_rebuilds_reverse_lookup_after_alias_map_inplace_union() -> None:
    aliases = build_tool_name_aliases(
        ["project.read_documents"],
        policy="safe_ascii_only",
    )

    aliases |= {"project.search_documents": "project_search_documents"}

    assert decode_tool_name(
        "project_search_documents",
        tool_name_aliases=aliases,
    ) == "project.search_documents"


def test_tool_name_alias_map_pop_preserves_dict_key_error_semantics() -> None:
    aliases = build_tool_name_aliases(
        ["project.read_documents"],
        policy="safe_ascii_only",
    )

    with pytest.raises(KeyError):
        aliases.pop("project.search_documents")


def test_tool_name_alias_map_setdefault_preserves_dict_none_default() -> None:
    aliases = ToolNameAliasMap({"project.read_documents": "project_read_documents"})

    value = aliases.setdefault("project.search_documents")

    assert value is None
    assert "project.search_documents" in aliases
    assert aliases["project.search_documents"] is None
