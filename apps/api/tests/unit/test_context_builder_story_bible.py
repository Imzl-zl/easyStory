from __future__ import annotations

from app.modules.context.engine import create_context_builder
from app.modules.context.models import StoryFact
from app.modules.workflow.models import ChapterTask
from tests.unit.context_builder_test_support import (
    build_context,
    create_content_with_version,
)
from tests.unit.models.helpers import create_project, create_workflow


def test_build_context_story_bible_excludes_confirmed_conflicts(db) -> None:
    builder = create_context_builder()
    project = create_project(
        db,
        project_setting={"protagonist": {"name": "林渊", "goal": "进入宗门"}},
    )
    workflow = create_workflow(db, project=project)
    outline_version = create_content_with_version(db, project.id, "outline", "大纲", "故事大纲")
    create_content_with_version(db, project.id, "opening_plan", "开篇设计", "前三章节奏规划")
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

    variables, report = build_context(
        builder,
        db,
        project.id,
        chapter_number=2,
        workflow_execution_id=workflow.id,
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
    outline_version = create_content_with_version(db, project.id, "outline", "大纲", "故事大纲")
    create_content_with_version(db, project.id, "opening_plan", "开篇设计", "前三章节奏规划")
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

    variables, report = build_context(
        builder,
        db,
        project.id,
        chapter_number=2,
        workflow_execution_id=workflow.id,
    )

    assert "已经进入内门" in variables["story_bible"]
    assert "仍在外门" not in variables["story_bible"]
    story_bible_report = next(item for item in report["sections"] if item["type"] == "story_bible")
    assert story_bible_report["items_count"] == 1
