import asyncio

import pytest

from app.modules.content.service import (
    StoryAssetSaveDTO,
    create_story_asset_service,
)
from app.shared.runtime.errors import BusinessRuleError
from tests.unit.async_service_support import async_db

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

    result = asyncio.run(
        service.save_asset_draft(
            async_db(db),
            project.id,
            "outline",
            StoryAssetSaveDTO(
                title="主线大纲",
                content_text="第一幕：主角入宗。\n第二幕：查出真相。",
                change_summary="初版大纲",
            ),
        )
    )

    assert result.content_type == "outline"
    assert result.status == "draft"
    assert result.version_number == 1
    assert "第一幕" in result.content_text
    assert result.impact.has_impact is False
    assert result.impact.total_affected_entries == 0
    assert result.impact.items == []


def test_get_asset_returns_current_outline_version(db):
    project = create_project(db, project_setting=ready_project_setting())
    service = create_story_asset_service()
    asyncio.run(
        service.save_asset_draft(
            async_db(db),
            project.id,
            "outline",
            StoryAssetSaveDTO(
                title="主线大纲",
                content_text="第一幕：主角入宗。",
                change_summary="初版大纲",
            ),
        )
    )

    result = asyncio.run(service.get_asset(async_db(db), project.id, "outline"))

    assert result.title == "主线大纲"
    assert result.status == "draft"
    assert result.content_text == "第一幕：主角入宗。"


def test_scaffold_preparation_assets_create_blank_current_versions(db):
    project = create_project(db)
    service = create_story_asset_service()

    asyncio.run(service.scaffold_preparation_assets(async_db(db), project.id))

    outline = asyncio.run(service.get_asset(async_db(db), project.id, "outline"))
    opening_plan = asyncio.run(service.get_asset(async_db(db), project.id, "opening_plan"))

    assert outline.title == "大纲"
    assert outline.status == "draft"
    assert outline.version_number == 1
    assert outline.content_text == ""
    assert opening_plan.title == "开篇设计"
    assert opening_plan.status == "draft"
    assert opening_plan.version_number == 1
    assert opening_plan.content_text == ""


def test_save_outline_allows_missing_project_setting(db):
    project = create_project(db)
    service = create_story_asset_service()

    result = asyncio.run(
        service.save_asset_draft(
            async_db(db),
            project.id,
            "outline",
            StoryAssetSaveDTO(title="主线大纲", content_text="故事从这里开始"),
        )
    )

    assert result.content_type == "outline"
    assert result.status == "draft"


def test_save_opening_plan_requires_approved_outline(db):
    project = create_project(db, project_setting=ready_project_setting())
    service = create_story_asset_service()
    asyncio.run(
        service.save_asset_draft(
            async_db(db),
            project.id,
            "outline",
            StoryAssetSaveDTO(title="主线大纲", content_text="大纲草稿"),
        )
    )

    try:
        asyncio.run(
            service.save_asset_draft(
                async_db(db),
                project.id,
                "opening_plan",
                StoryAssetSaveDTO(title="开篇设计", content_text="前三章策略"),
            )
        )
    except BusinessRuleError as exc:
        assert "outline 必须先确认" in exc.message
    else:
        raise AssertionError("expected BusinessRuleError")


def test_approve_asset_rejects_blank_scaffold_version(db):
    project = create_project(db, project_setting=ready_project_setting())
    service = create_story_asset_service()
    asyncio.run(service.scaffold_preparation_assets(async_db(db), project.id))

    with pytest.raises(BusinessRuleError, match="outline 内容为空，无法确认"):
        asyncio.run(service.approve_asset(async_db(db), project.id, "outline"))


def test_approve_asset_returns_empty_impact(db):
    project = create_project(db, project_setting=ready_project_setting())
    service = create_story_asset_service()
    asyncio.run(
        service.save_asset_draft(
            async_db(db),
            project.id,
            "outline",
            StoryAssetSaveDTO(title="主线大纲", content_text="大纲首版"),
        )
    )

    result = asyncio.run(service.approve_asset(async_db(db), project.id, "outline"))

    assert result.status == "approved"
    assert result.impact.has_impact is False
    assert result.impact.total_affected_entries == 0
    assert result.impact.items == []


def test_outline_change_marks_all_approved_downstream_content_and_tasks_stale(db):
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

    result = asyncio.run(
        service.save_asset_draft(
            async_db(db),
            project.id,
            "outline",
            StoryAssetSaveDTO(title="大纲", content_text="新大纲"),
        )
    )

    db.refresh(opening_plan)
    db.refresh(chapter1)
    db.refresh(chapter4)
    db.refresh(chapter_task)

    assert result.version_number == 2
    assert result.impact.has_impact is True
    assert result.impact.total_affected_entries == 4
    assert opening_plan.status == "stale"
    assert chapter1.status == "stale"
    assert chapter4.status == "stale"
    assert chapter_task.status == "stale"
    assert [item.target for item in result.impact.items] == [
        "opening_plan",
        "chapter",
        "chapter_tasks",
    ]
    assert [item.count for item in result.impact.items] == [1, 2, 1]


def test_opening_plan_change_marks_early_chapters_and_tasks_stale(db):
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

    result = asyncio.run(
        service.save_asset_draft(
            async_db(db),
            project.id,
            "opening_plan",
            StoryAssetSaveDTO(title="开篇设计", content_text="新的前三章策略"),
        )
    )

    db.refresh(chapter1)
    db.refresh(chapter4)
    db.refresh(chapter_task)
    assert result.impact.has_impact is True
    assert result.impact.total_affected_entries == 2
    assert [item.target for item in result.impact.items] == ["chapter", "chapter_tasks"]
    assert [item.count for item in result.impact.items] == [1, 1]
    assert chapter1.status == "stale"
    assert chapter4.status == "approved"
    assert chapter_task.status == "stale"
