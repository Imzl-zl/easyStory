from app.modules.assistant.service.context.assistant_context_compaction_support import (
    _resolve_summary_token_budgets,
)
from app.modules.assistant.service.context.assistant_prompt_support import (
    build_document_context_injection_snapshot,
    build_document_context_prompt_snapshot,
    is_document_context_projection_collapsed,
    resolve_document_context_projection_mode,
)


def test_resolve_summary_token_budgets_allows_small_compaction_candidates() -> None:
    budgets = _resolve_summary_token_budgets(36)

    assert budgets[-1] == 8
    assert min(budgets) == 8
    assert any(candidate < 24 for candidate in budgets)


def test_build_document_context_prompt_snapshot_keeps_prompt_visible_fields() -> None:
    snapshot = build_document_context_prompt_snapshot(
        {
            "active_path": "设定/人物.md",
            "active_document_ref": "project_file:characters",
            "active_binding_version": "binding:v1",
            "selected_paths": ["设定/人物.md", "数据层/人物关系.json"],
            "selected_document_refs": ["project_file:characters", "project_file:relations"],
            "active_buffer_state": {
                "dirty": True,
                "base_version": "version:v1",
                "buffer_hash": "buffer:abc",
                "source": "trusted_buffer",
            },
            "catalog_version": "catalog:v1",
        }
    )

    assert snapshot is not None
    assert snapshot["active_path"] == "设定/人物.md"
    assert snapshot["selected_paths"] == ["设定/人物.md", "数据层/人物关系.json"]
    assert snapshot["selected_document_refs"] == [
        "project_file:characters",
        "project_file:relations",
    ]
    assert snapshot["catalog_version"] == "catalog:v1"


def test_document_context_projection_mode_and_collapse_follow_prompt_projection() -> None:
    source_document_context = {
        "active_path": "设定/人物.md",
        "selected_paths": ["设定/人物.md", "数据层/人物关系.json"],
    }
    projected_snapshot = build_document_context_prompt_snapshot(source_document_context)

    assert resolve_document_context_projection_mode(projected_snapshot) == "full"
    assert is_document_context_projection_collapsed(
        source_document_context,
        projected_snapshot,
    ) is False
    assert resolve_document_context_projection_mode(None) == "omitted"


def test_build_document_context_injection_snapshot_prefers_recovery_view() -> None:
    snapshot = build_document_context_injection_snapshot(
        {
            "active_path": "设定/人物.md",
            "selected_paths": ["设定/人物.md"],
        },
        document_context_recovery_snapshot={
            "active_path": "设定/人物.md",
            "active_document_ref": "project_file:characters",
            "active_binding_version": "binding:v2",
            "selected_paths": ["设定/人物.md"],
            "selected_document_refs": ["project_file:characters"],
            "catalog_version": "catalog:v2",
        },
    )

    assert snapshot is not None
    assert snapshot["active_document_ref"] == "project_file:characters"
    assert snapshot["active_binding_version"] == "binding:v2"
    assert snapshot["selected_document_refs"] == ["project_file:characters"]
