from __future__ import annotations

import shutil
import uuid

import pytest

from app.modules.config_registry.infrastructure.config_loader import ConfigLoader
from app.modules.context.engine import ContextBuilder, ContextOverflowError, create_context_builder
from app.shared.runtime.token_counter import ModelPricing
from tests.unit.context_builder_test_support import API_ROOT, CONFIG_ROOT, make_section


def test_match_patterns_and_merge_rules_for_chapter_gen() -> None:
    workflow = ConfigLoader(CONFIG_ROOT).load_workflow("workflow.xuanhuan_manual")
    builder = create_context_builder()

    merged = builder.merge_rules(
        workflow.context_injection.default_inject,
        workflow.context_injection.rules,
        "chapter_gen",
        [],
    )

    inject_types = {item.inject_type for item in merged}
    assert inject_types == {
        "project_setting",
        "outline",
        "opening_plan",
        "chapter_task",
        "previous_chapters",
        "story_bible",
    }


def test_truncate_context_keeps_priority_one_sections() -> None:
    builder = create_context_builder()
    sections = [
        make_section(builder, "project_setting", 600, 1, 0, True),
        make_section(builder, "chapter_task", 300, 1, 0, True),
        make_section(builder, "previous_chapters", 1500, 5, 500, False),
        make_section(builder, "outline", 1200, 8, 200, False),
    ]

    truncated = builder.truncate_context(sections, budget=900, model="gpt-4o")

    assert truncated[0].token_count == sections[0].token_count
    assert truncated[1].token_count == sections[1].token_count
    assert builder._total_tokens(truncated) <= 900
    assert any(item.status in {"truncated", "dropped"} for item in truncated[2:])


def test_ensure_model_window_raises_when_required_context_still_exceeds_window() -> None:
    temp_root = API_ROOT / ".pytest-tmp" / uuid.uuid4().hex
    temp_root.mkdir(parents=True, exist_ok=True)
    config_path = temp_root / "pricing.yaml"
    config_path.write_text(
        'version: "test"\nmodels:\n  tiny-model:\n    input_per_1k: 0.001\n    output_per_1k: 0.002\n    context_window: 100\n',
        encoding="utf-8",
    )

    try:
        builder = create_context_builder(model_pricing=ModelPricing(config_path))
        sections = [
            make_section(builder, "project_setting", 240, 1, 0, True),
            make_section(builder, "chapter_task", 240, 1, 0, True),
        ]

        with pytest.raises(ContextOverflowError, match="context_window"):
            builder.ensure_model_window("tiny-model", sections)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_make_section_uses_context_builder_token_counter() -> None:
    builder = create_context_builder()

    section = make_section(builder, "outline", 120, 8, 200, False)

    assert isinstance(builder, ContextBuilder)
    assert section.token_count == builder.token_counter.count(section.content, "gpt-4o")
