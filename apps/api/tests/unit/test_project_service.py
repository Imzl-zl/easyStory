from app.modules.project.service import ProjectService, ProjectSettingUpdateDTO

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

    result = ProjectService().update_project_setting(
        db,
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

    db.refresh(project)
    db.refresh(outline)
    db.refresh(opening_plan)
    db.refresh(chapter)
    db.refresh(chapter_task)

    assert result.genre == "仙侠"
    assert result.target_words == 800000
    assert project.genre == "仙侠"
    assert project.target_words == 800000
    assert outline.status == "stale"
    assert opening_plan.status == "stale"
    assert chapter.status == "stale"
    assert chapter_task.status == "stale"


def test_check_setting_completeness_returns_blocked_and_warning_issues(db):
    project = create_project(
        db,
        project_setting={
            "genre": "玄幻",
            "protagonist": {"name": "林渊"},
        },
    )

    result = ProjectService().check_setting_completeness(db, project.id)

    issue_fields = {issue.field: issue.level for issue in result.issues}
    assert result.status == "blocked"
    assert issue_fields["protagonist.identity"] == "blocked"
    assert issue_fields["protagonist.goal"] == "blocked"
    assert issue_fields["core_conflict"] == "blocked"
    assert issue_fields["world_setting"] == "blocked"
    assert issue_fields["tone"] == "warning"
    assert issue_fields["scale"] == "warning"
