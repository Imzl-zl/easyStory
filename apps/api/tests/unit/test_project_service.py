import asyncio

from app.modules.content.models import Content, ContentVersion

from app.modules.project.service import ProjectService, ProjectSettingUpdateDTO
from tests.unit.async_service_support import async_db

from tests.unit.models.helpers import (
    create_chapter_task,
    create_content,
    create_content_version,
    create_project,
    create_workflow,
    ready_project_setting,
)


def test_update_project_setting_syncs_summary_and_marks_related_content_stale(db):
    project = create_project(
        db,
        project_setting=ready_project_setting(
            protagonist={"name": "林渊", "identity": "少年", "goal": "变强"},
            world_setting={"world_rules": "灵气修炼"},
            core_conflict="宗门压制",
            scale={"target_words": 500000},
        ),
    )
    workflow = create_workflow(db, project=project)
    outline = create_content(
        db,
        project=project,
        content_type="outline",
        title="大纲",
        chapter_number=None,
    )
    outline.status = "approved"
    outline.chapter_number = None
    opening_plan = create_content(
        db,
        project=project,
        content_type="opening_plan",
        title="开篇设计",
        chapter_number=None,
    )
    opening_plan.status = "approved"
    chapter = create_content(db, project=project, title="第一章")
    chapter.status = "approved"
    chapter_task = create_chapter_task(
        db,
        workflow=workflow,
        chapter_number=1,
        title="第一章",
        brief="旧章节计划",
        status="pending",
    )
    db.commit()
    create_content_version(db, content=outline, content_text="旧大纲", version_number=1)
    create_content_version(
        db,
        content=opening_plan,
        content_text="旧开篇",
        version_number=1,
    )

    result = asyncio.run(
        ProjectService().update_project_setting(
            async_db(db),
            project.id,
            ProjectSettingUpdateDTO(
                project_setting={
                    "genre": "仙侠",
                    "tone": "冷峻",
                    "core_conflict": "主角在宗门追杀中求生",
                    "protagonist": {
                        "name": "林渊",
                        "identity": "弃徒",
                        "goal": "重返内门",
                    },
                    "world_setting": {
                        "era_baseline": "宗门割据时代",
                        "world_rules": "境界压制",
                    },
                    "scale": {"target_words": 800000},
                }
            ),
        )
    )

    db.refresh(project)
    db.refresh(outline)
    db.refresh(opening_plan)
    db.refresh(chapter)
    db.refresh(chapter_task)

    assert result.genre == "仙侠"
    assert result.target_words == 800000
    assert result.impact.has_impact is True
    assert result.impact.total_affected_entries == 4
    assert [(item.target, item.count) for item in result.impact.items] == [
        ("outline", 1),
        ("opening_plan", 1),
        ("chapter", 1),
        ("chapter_tasks", 1),
    ]
    assert project.genre == "仙侠"
    assert project.target_words == 800000
    assert outline.status == "stale"
    assert opening_plan.status == "stale"
    assert chapter.status == "stale"
    assert chapter_task.status == "stale"


def test_update_project_setting_returns_empty_impact_when_value_is_unchanged(db):
    project = create_project(
        db,
        project_setting=ready_project_setting(),
    )

    result = asyncio.run(
        ProjectService().update_project_setting(
            async_db(db),
            project.id,
            ProjectSettingUpdateDTO(project_setting=ready_project_setting()),
        )
    )

    assert result.impact.has_impact is False
    assert result.impact.total_affected_entries == 0
    assert result.impact.items == []


def test_check_setting_completeness_returns_blocked_and_warning_issues(db):
    project = create_project(
        db,
        project_setting={
            "genre": "玄幻",
            "protagonist": {"name": "林渊"},
        },
    )

    result = asyncio.run(ProjectService().check_setting_completeness(async_db(db), project.id))

    issue_fields = {issue.field: issue.level for issue in result.issues}
    assert result.status == "blocked"
    assert issue_fields["protagonist.identity"] == "blocked"
    assert issue_fields["protagonist.goal"] == "blocked"
    assert issue_fields["core_conflict"] == "blocked"
    assert issue_fields["world_setting"] == "blocked"
    assert issue_fields["tone"] == "warning"
    assert issue_fields["scale"] == "warning"


def test_get_preparation_status_points_to_setting_when_project_is_incomplete(db):
    project = create_project(
        db,
        project_setting={"genre": "玄幻"},
    )

    result = asyncio.run(ProjectService().get_preparation_status(async_db(db), project.id))

    assert result.setting.status == "blocked"
    assert result.outline.step_status == "not_started"
    assert result.opening_plan.step_status == "not_started"
    assert result.chapter_tasks.step_status == "not_started"
    assert result.can_start_workflow is False
    assert result.next_step == "setting"


def test_get_preparation_status_identifies_workflow_gate_when_assets_ready(db):
    project = create_project(
        db,
        project_setting=ready_project_setting(),
    )
    _create_story_asset(db, project.id, "outline", "approved", "主线大纲")
    _create_story_asset(db, project.id, "opening_plan", "approved", "前三章开篇设计")

    result = asyncio.run(ProjectService().get_preparation_status(async_db(db), project.id))

    assert result.setting.status == "ready"
    assert result.outline.step_status == "approved"
    assert result.opening_plan.step_status == "approved"
    assert result.chapter_tasks.step_status == "not_started"
    assert result.can_start_workflow is True
    assert result.next_step == "workflow"


def test_get_preparation_status_flags_stale_tasks_under_active_workflow(db):
    project = create_project(
        db,
        project_setting=ready_project_setting(),
    )
    workflow = create_workflow(
        db,
        project=project,
        status="paused",
        current_node_id="chapter_gen",
    )
    _create_story_asset(db, project.id, "outline", "approved", "主线大纲")
    _create_story_asset(db, project.id, "opening_plan", "approved", "前三章开篇设计")
    create_chapter_task(
        db,
        workflow=workflow,
        chapter_number=1,
        title="第一章",
        brief="旧任务",
        status="stale",
    )

    result = asyncio.run(ProjectService().get_preparation_status(async_db(db), project.id))

    assert result.active_workflow is not None
    assert result.active_workflow.execution_id == workflow.id
    assert result.chapter_tasks.step_status == "stale"
    assert result.chapter_tasks.counts.stale == 1
    assert result.can_start_workflow is False
    assert result.next_step == "chapter_tasks"


def _create_story_asset(
    db,
    project_id,
    content_type: str,
    status: str,
    content_text: str,
) -> None:
    content = Content(
        project_id=project_id,
        content_type=content_type,
        title="大纲" if content_type == "outline" else "开篇设计",
        chapter_number=None,
        status=status,
    )
    db.add(content)
    db.flush()
    db.add(
        ContentVersion(
            content_id=content.id,
            version_number=1,
            content_text=content_text,
            is_current=True,
        )
    )
    db.commit()
