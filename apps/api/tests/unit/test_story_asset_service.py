from app.modules.content.service import (
    StoryAssetSaveDTO,
    create_story_asset_service,
)
from app.shared.runtime.errors import BusinessRuleError

from tests.unit.models.helpers import (
    create_chapter_task,
    create_content,
    create_content_version,
    create_project,
    create_workflow,
    ready_project_setting,
)


def test_save_outline_draft_creates_versioned_asset(db):
    project = create_project(db, project_setting=ready_project_setting())
    service = create_story_asset_service()

    result = service.save_asset_draft(
        db,
        project.id,
        "outline",
        StoryAssetSaveDTO(
            title="主线大纲",
            content_text="第一幕：主角入宗。\n第二幕：查出真相。",
            change_summary="初版大纲",
        ),
    )

    assert result.content_type == "outline"
    assert result.status == "draft"
    assert result.version_number == 1
    assert "第一幕" in result.content_text


def test_save_outline_requires_non_blocked_project_setting(db):
    project = create_project(db)
    service = create_story_asset_service()

    try:
        service.save_asset_draft(
            db,
            project.id,
            "outline",
            StoryAssetSaveDTO(title="主线大纲", content_text="故事从这里开始"),
        )
    except BusinessRuleError as exc:
        assert "项目设定未完成" in exc.message
    else:
        raise AssertionError("expected BusinessRuleError")


def test_save_opening_plan_requires_approved_outline(db):
    project = create_project(db, project_setting=ready_project_setting())
    service = create_story_asset_service()
    service.save_asset_draft(
        db,
        project.id,
        "outline",
        StoryAssetSaveDTO(title="主线大纲", content_text="大纲草稿"),
    )

    try:
        service.save_asset_draft(
            db,
            project.id,
            "opening_plan",
            StoryAssetSaveDTO(title="开篇设计", content_text="前三章策略"),
        )
    except BusinessRuleError as exc:
        assert "outline 必须先确认" in exc.message
    else:
        raise AssertionError("expected BusinessRuleError")


def test_outline_change_marks_opening_plan_and_early_chapters_stale(db):
    project = create_project(db, project_setting=ready_project_setting())
    service = create_story_asset_service()
    workflow = create_workflow(db, project=project)
    outline = create_content(
        db,
        project=project,
        content_type="outline",
        title="大纲",
        chapter_number=None,
    )
    outline.status = "approved"
    opening_plan = create_content(
        db,
        project=project,
        content_type="opening_plan",
        title="开篇设计",
        chapter_number=None,
    )
    opening_plan.status = "approved"
    chapter1 = create_content(db, project=project, title="第一章")
    chapter1.status = "approved"
    chapter4 = create_content(db, project=project, title="第四章", chapter_number=4)
    chapter4.status = "approved"
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

    result = service.save_asset_draft(
        db,
        project.id,
        "outline",
        StoryAssetSaveDTO(title="大纲", content_text="新大纲"),
    )

    db.refresh(opening_plan)
    db.refresh(chapter1)
    db.refresh(chapter4)
    db.refresh(chapter_task)

    assert result.version_number == 2
    assert opening_plan.status == "stale"
    assert chapter1.status == "stale"
    assert chapter4.status == "stale"
    assert chapter_task.status == "stale"


def test_opening_plan_change_marks_chapter_tasks_stale(db):
    project = create_project(db, project_setting=ready_project_setting())
    service = create_story_asset_service()
    workflow = create_workflow(db, project=project)
    outline = create_content(
        db,
        project=project,
        content_type="outline",
        title="大纲",
        chapter_number=None,
    )
    outline.status = "approved"
    opening_plan = create_content(
        db,
        project=project,
        content_type="opening_plan",
        title="开篇设计",
        chapter_number=None,
    )
    opening_plan.status = "approved"
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

    service.save_asset_draft(
        db,
        project.id,
        "opening_plan",
        StoryAssetSaveDTO(title="开篇设计", content_text="新的前三章策略"),
    )

    db.refresh(chapter_task)
    assert chapter_task.status == "stale"
