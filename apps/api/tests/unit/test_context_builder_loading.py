from __future__ import annotations

import pytest

from app.modules.context.engine import create_context_builder
from app.modules.context.engine.errors import RequiredContextMissingError
from app.modules.workflow.models import ChapterTask
from app.shared.runtime.template_renderer import SkillTemplateRenderer
from tests.unit.context_builder_test_support import (
    build_context,
    create_content_with_version,
)
from tests.unit.models.helpers import create_project, create_workflow


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
    create_content_with_version(db, project.id, "outline", "大纲", "故事大纲")
    create_content_with_version(db, project.id, "opening_plan", "开篇设计", "前三章节奏规划")
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

    variables, report = build_context(
        builder,
        db,
        project.id,
        chapter_number=1,
        workflow_execution_id=workflow.id,
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
    create_content_with_version(db, project.id, "outline", "大纲", "故事大纲")
    create_content_with_version(
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

    variables, report = build_context(
        builder,
        db,
        project.id,
        chapter_number=4,
        workflow_execution_id=workflow.id,
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
    create_content_with_version(db, project.id, "outline", "大纲", "故事大纲")
    create_content_with_version(
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
        build_context(
            builder,
            db,
            project.id,
            chapter_number=1,
            workflow_execution_id=workflow.id,
        )


def test_build_context_rejects_stale_chapter_task(db) -> None:
    builder = create_context_builder()
    project = create_project(
        db,
        project_setting={"protagonist": {"name": "林渊", "goal": "变强"}},
    )
    workflow = create_workflow(db, project=project)
    create_content_with_version(db, project.id, "outline", "大纲", "故事大纲")
    create_content_with_version(db, project.id, "opening_plan", "开篇设计", "前三章节奏规划")
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
        build_context(
            builder,
            db,
            project.id,
            chapter_number=1,
            workflow_execution_id=workflow.id,
        )
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
    create_content_with_version(db, project.id, "outline", "大纲", "故事大纲")
    create_content_with_version(db, project.id, "opening_plan", "开篇设计", "前三章节奏规划")
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

    variables, report = build_context(
        builder,
        db,
        project.id,
        chapter_number=1,
        workflow_execution_id=workflow.id,
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
