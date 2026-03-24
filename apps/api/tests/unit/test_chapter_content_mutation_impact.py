import asyncio

from app.modules.content.service import ChapterSaveDTO, create_chapter_content_service
from tests.unit.async_service_support import async_db
from tests.unit.models.helpers import (
    create_content,
    create_content_version,
    create_project,
    ready_project_setting,
)


def test_save_chapter_draft_returns_downstream_impact_summary(db):
    project = create_project(db, project_setting=ready_project_setting())
    _create_preparation_assets(db, project)
    service = create_chapter_content_service()
    _create_chapter(db, project, 1, "第一章", "第一章正文", status="approved")
    _create_chapter(db, project, 2, "第二章", "第二章正文", status="approved")
    _create_chapter(db, project, 3, "第三章", "第三章正文", status="draft")

    result = asyncio.run(
        service.save_chapter_draft(
            async_db(db),
            project.id,
            1,
            ChapterSaveDTO(title="第一章", content_text="第一章重写版"),
        )
    )

    assert result.impact.has_impact is True
    assert result.impact.total_affected_entries == 1
    assert result.impact.items[0].target == "chapter"
    assert result.impact.items[0].action == "mark_stale"
    assert result.impact.items[0].count == 1


def test_save_chapter_draft_returns_empty_impact_summary_without_downstream_change(db):
    project = create_project(db, project_setting=ready_project_setting())
    _create_preparation_assets(db, project)
    service = create_chapter_content_service()
    _create_chapter(db, project, 1, "第一章", "第一章正文", status="approved")
    _create_chapter(db, project, 2, "第二章", "第二章正文", status="draft")

    result = asyncio.run(
        service.save_chapter_draft(
            async_db(db),
            project.id,
            1,
            ChapterSaveDTO(title="第一章", content_text="第一章重写版"),
        )
    )

    assert result.impact.has_impact is False
    assert result.impact.total_affected_entries == 0
    assert result.impact.items == []


def test_rollback_version_returns_downstream_impact_summary(db):
    project = create_project(db, project_setting=ready_project_setting())
    _create_preparation_assets(db, project)
    service = create_chapter_content_service()
    chapter = _create_chapter(db, project, 2, "第二章", "第二章正文", status="approved")
    _create_chapter(db, project, 3, "第三章", "第三章正文", status="approved")
    _version_by_number(chapter, 1).is_current = False
    db.commit()
    create_content_version(
        db,
        content=chapter,
        version_number=2,
        content_text="第二章重写版",
        is_current=True,
        change_summary="重写",
    )

    result = asyncio.run(service.rollback_version(async_db(db), project.id, 2, 1))

    assert result.impact.has_impact is True
    assert result.impact.total_affected_entries == 1
    assert result.impact.items[0].target == "chapter"
    assert result.impact.items[0].count == 1


def _create_preparation_assets(db, project):
    outline = create_content(
        db,
        project=project,
        content_type="outline",
        chapter_number=None,
        title="大纲",
        status="approved",
    )
    opening_plan = create_content(
        db,
        project=project,
        content_type="opening_plan",
        chapter_number=None,
        title="开篇设计",
        status="approved",
    )
    create_content_version(db, content=outline, version_number=1, content_text="大纲内容")
    create_content_version(
        db,
        content=opening_plan,
        version_number=1,
        content_text="开篇设计内容",
    )


def _create_chapter(db, project, chapter_number, title, content_text, *, status="draft"):
    content = create_content(
        db,
        project=project,
        chapter_number=chapter_number,
        title=title,
        status=status,
    )
    create_content_version(
        db,
        content=content,
        version_number=1,
        content_text=content_text,
        is_current=True,
    )
    return content


def _version_by_number(content, version_number):
    for version in content.versions:
        if version.version_number == version_number:
            return version
    raise AssertionError(f"version not found: {version_number}")
