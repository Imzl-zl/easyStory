import shutil
import uuid
from pathlib import Path

import pytest

from app.modules.config_registry.infrastructure.config_loader import ConfigLoader
from app.modules.context.engine import (
    ContextBuilder,
    ContextOverflowError,
    ContextSection,
    create_context_builder,
)
from app.modules.context.engine.errors import RequiredContextMissingError
from app.modules.content.models import Content, ContentVersion
from app.modules.context.models import StoryFact
from app.modules.workflow.models import ChapterTask
from app.shared.runtime.template_renderer import SkillTemplateRenderer
from app.shared.runtime.token_counter import ModelPricing
from tests.unit.models.helpers import create_project, create_workflow

PROJECT_ROOT = Path(__file__).resolve().parents[4]
API_ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOT = PROJECT_ROOT / "config"


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


def test_build_context_for_first_chapter_marks_optional_sources_not_applicable(db) -> None:
    builder = create_context_builder()
    project = create_project(
        db,
        project_setting={
            "genre": "玄幻",
            "protagonist": {"name": "林渊", "goal": "进入宗门"},
            "world_setting": {"name": "九州大陆"},
        },
    )
    workflow = create_workflow(db, project=project)
    _create_content_with_version(db, project.id, "outline", "大纲", "故事大纲")
    _create_content_with_version(db, project.id, "opening_plan", "开篇设计", "前三章节奏规划")
    db.add(
        ChapterTask(
            project_id=project.id,
            workflow_execution_id=workflow.id,
            chapter_number=1,
            title="第一章",
            brief="主角初登场",
            key_characters=["林渊"],
            key_events=["进入宗门"],
        )
    )
    db.commit()

    variables, report = builder.build_context(
        project.id,
        _chapter_context_rules(),
        db,
        chapter_number=1,
        workflow_execution_id=workflow.id,
        model="gpt-4o",
    )

    assert "林渊" in variables["project_setting"]
    assert variables["outline"] == "故事大纲"
    assert variables["opening_plan"] == "前三章节奏规划"
    assert "主角初登场" in variables["chapter_task"]
    assert variables["previous_content"] == ""
    assert variables["story_bible"] == ""
    statuses = {item["type"]: item["status"] for item in report["sections"]}
    assert statuses["previous_chapters"] == "not_applicable"
    assert statuses["story_bible"] == "not_applicable"


def test_build_context_degrades_opening_plan_after_third_chapter(db) -> None:
    builder = create_context_builder()
    project = create_project(
        db,
        project_setting={"protagonist": {"name": "林渊", "goal": "变强"}},
    )
    workflow = create_workflow(db, project=project)
    _create_content_with_version(db, project.id, "outline", "大纲", "故事大纲")
    _create_content_with_version(
        db,
        project.id,
        "opening_plan",
        "开篇设计",
        "这是一个很长的开篇设计。" * 40,
    )
    db.add(
        ChapterTask(
            project_id=project.id,
            workflow_execution_id=workflow.id,
            chapter_number=4,
            title="第四章",
            brief="开篇阶段结束",
        )
    )
    db.commit()

    variables, report = builder.build_context(
        project.id,
        _chapter_context_rules(),
        db,
        chapter_number=4,
        workflow_execution_id=workflow.id,
        model="gpt-4o",
    )

    assert variables["opening_plan"].startswith("开篇设计摘要")
    opening_plan_report = next(item for item in report["sections"] if item["type"] == "opening_plan")
    assert opening_plan_report["status"] == "degraded"


def test_build_context_rejects_unapproved_opening_plan(db) -> None:
    builder = create_context_builder()
    project = create_project(
        db,
        project_setting={"protagonist": {"name": "林渊", "goal": "变强"}},
    )
    workflow = create_workflow(db, project=project)
    _create_content_with_version(db, project.id, "outline", "大纲", "故事大纲")
    _create_content_with_version(
        db,
        project.id,
        "opening_plan",
        "开篇设计",
        "草稿开篇设计",
        status="draft",
    )
    db.add(
        ChapterTask(
            project_id=project.id,
            workflow_execution_id=workflow.id,
            chapter_number=1,
            title="第一章",
            brief="主角初登场",
        )
    )
    db.commit()

    with pytest.raises(RequiredContextMissingError):
        builder.build_context(
            project.id,
            _chapter_context_rules(),
            db,
            chapter_number=1,
            workflow_execution_id=workflow.id,
            model="gpt-4o",
        )


def test_build_context_rejects_stale_chapter_task(db) -> None:
    builder = create_context_builder()
    project = create_project(
        db,
        project_setting={"protagonist": {"name": "林渊", "goal": "变强"}},
    )
    workflow = create_workflow(db, project=project)
    _create_content_with_version(db, project.id, "outline", "大纲", "故事大纲")
    _create_content_with_version(
        db,
        project.id,
        "opening_plan",
        "开篇设计",
        "前三章节奏规划",
    )
    db.add(
        ChapterTask(
            project_id=project.id,
            workflow_execution_id=workflow.id,
            chapter_number=1,
            title="第一章",
            brief="已经过期的章节任务",
            status="stale",
        )
    )
    db.commit()

    with pytest.raises(RequiredContextMissingError):
        builder.build_context(
            project.id,
            _chapter_context_rules(),
            db,
            chapter_number=1,
            workflow_execution_id=workflow.id,
            model="gpt-4o",
        )


def test_build_context_story_bible_excludes_confirmed_conflicts(db) -> None:
    builder = create_context_builder()
    project = create_project(
        db,
        project_setting={"protagonist": {"name": "林渊", "goal": "进入宗门"}},
    )
    workflow = create_workflow(db, project=project)
    outline_version = _create_content_with_version(db, project.id, "outline", "大纲", "故事大纲")
    _create_content_with_version(db, project.id, "opening_plan", "开篇设计", "前三章节奏规划")
    db.add(
        ChapterTask(
            project_id=project.id,
            workflow_execution_id=workflow.id,
            chapter_number=2,
            title="第二章",
            brief="进入宗门",
        )
    )
    db.add_all(
        [
            StoryFact(
                project_id=project.id,
                chapter_number=1,
                source_content_version_id=outline_version.id,
                fact_type="character_state",
                subject="林渊",
                content="已进入宗门",
                is_active=True,
                conflict_status="none",
            ),
            StoryFact(
                project_id=project.id,
                chapter_number=1,
                source_content_version_id=outline_version.id,
                fact_type="character_state",
                subject="林渊",
                content="仍在山下",
                is_active=True,
                conflict_status="confirmed",
            ),
        ]
    )
    db.commit()

    variables, report = builder.build_context(
        project.id,
        _chapter_context_rules(),
        db,
        chapter_number=2,
        workflow_execution_id=workflow.id,
        model="gpt-4o",
    )

    assert "已进入宗门" in variables["story_bible"]
    assert "仍在山下" not in variables["story_bible"]
    story_bible_report = next(item for item in report["sections"] if item["type"] == "story_bible")
    assert story_bible_report["items_count"] == 1


def test_build_context_story_bible_excludes_superseded_facts(db) -> None:
    builder = create_context_builder()
    project = create_project(
        db,
        project_setting={"protagonist": {"name": "林渊", "goal": "进入宗门"}},
    )
    workflow = create_workflow(db, project=project)
    outline_version = _create_content_with_version(db, project.id, "outline", "大纲", "故事大纲")
    _create_content_with_version(db, project.id, "opening_plan", "开篇设计", "前三章节奏规划")
    db.add(
        ChapterTask(
            project_id=project.id,
            workflow_execution_id=workflow.id,
            chapter_number=2,
            title="第二章",
            brief="进入宗门",
        )
    )
    superseding_fact = StoryFact(
        project_id=project.id,
        chapter_number=1,
        source_content_version_id=outline_version.id,
        fact_type="character_state",
        subject="林渊",
        content="已经进入内门",
        is_active=True,
        conflict_status="none",
    )
    db.add(superseding_fact)
    db.commit()
    db.refresh(superseding_fact)
    db.add(
        StoryFact(
            project_id=project.id,
            chapter_number=1,
            source_content_version_id=outline_version.id,
            fact_type="character_state",
            subject="林渊",
            content="仍在外门",
            is_active=True,
            conflict_status="none",
            superseded_by=superseding_fact.id,
        )
    )
    db.commit()

    variables, report = builder.build_context(
        project.id,
        _chapter_context_rules(),
        db,
        chapter_number=2,
        workflow_execution_id=workflow.id,
        model="gpt-4o",
    )

    assert "已经进入内门" in variables["story_bible"]
    assert "仍在外门" not in variables["story_bible"]
    story_bible_report = next(item for item in report["sections"] if item["type"] == "story_bible")
    assert story_bible_report["items_count"] == 1


def test_truncate_context_keeps_priority_one_sections() -> None:
    builder = create_context_builder()
    sections = [
        _make_section(builder, "project_setting", 600, 1, 0, True),
        _make_section(builder, "chapter_task", 300, 1, 0, True),
        _make_section(builder, "previous_chapters", 1500, 5, 500, False),
        _make_section(builder, "outline", 1200, 8, 200, False),
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
            _make_section(builder, "project_setting", 240, 1, 0, True),
            _make_section(builder, "chapter_task", 240, 1, 0, True),
        ]

        with pytest.raises(ContextOverflowError, match="context_window"):
            builder.ensure_model_window("tiny-model", sections)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_build_context_marks_unreferenced_sections_unused(db) -> None:
    builder = create_context_builder()
    renderer = SkillTemplateRenderer()
    project = create_project(
        db,
        project_setting={
            "genre": "玄幻",
            "protagonist": {"name": "林渊", "goal": "进入宗门"},
            "world_setting": {"name": "九州大陆"},
        },
    )
    workflow = create_workflow(db, project=project)
    _create_content_with_version(db, project.id, "outline", "大纲", "故事大纲")
    _create_content_with_version(db, project.id, "opening_plan", "开篇设计", "前三章节奏规划")
    db.add(
        ChapterTask(
            project_id=project.id,
            workflow_execution_id=workflow.id,
            chapter_number=1,
            title="第一章",
            brief="主角初登场",
        )
    )
    db.commit()

    variables, report = builder.build_context(
        project.id,
        _chapter_context_rules(),
        db,
        chapter_number=1,
        workflow_execution_id=workflow.id,
        model="gpt-4o",
        referenced_variables=renderer.referenced_variables(
            "{{ project_setting }}\n{{ chapter_task }}"
        ),
    )

    assert "project_setting" in variables
    assert "chapter_task" in variables
    assert "outline" not in variables
    assert "opening_plan" not in variables
    statuses = {item["type"]: item for item in report["sections"]}
    assert statuses["outline"]["status"] == "unused"
    assert statuses["outline"]["token_count"] == 0
    assert report["total_tokens"] < 200


def _chapter_context_rules():
    workflow = ConfigLoader(CONFIG_ROOT).load_workflow("workflow.xuanhuan_manual")
    return create_context_builder().merge_rules(
        workflow.context_injection.default_inject,
        workflow.context_injection.rules,
        "chapter_gen",
        [],
    )


def _create_content_with_version(
    db,
    project_id,
    content_type: str,
    title: str,
    text: str,
    *,
    chapter_number: int | None = None,
    status: str = "approved",
) -> ContentVersion:
    content = Content(
        project_id=project_id,
        content_type=content_type,
        title=title,
        chapter_number=chapter_number,
        status=status,
    )
    db.add(content)
    db.commit()
    db.refresh(content)
    version = ContentVersion(
        content_id=content.id,
        version_number=1,
        content_text=text,
        is_current=True,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def _make_section(
    builder: ContextBuilder,
    inject_type: str,
    text_length: int,
    priority: int,
    min_tokens: int,
    required: bool,
) -> ContextSection:
    content = "x" * text_length
    return ContextSection(
        inject_type=inject_type,
        variable_name=inject_type,
        content=content,
        priority=priority,
        min_tokens=min_tokens,
        required=required,
        token_count=builder.token_counter.count(content, "gpt-4o"),
    )
