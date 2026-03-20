from app.modules.content.service import ChapterSaveDTO, create_chapter_content_service
from app.shared.runtime.errors import BusinessRuleError

from tests.unit.models.helpers import (
    create_content,
    create_content_version,
    create_project,
    create_workflow,
    create_chapter_task,
    ready_project_setting,
)


def test_save_chapter_draft_creates_versioned_chapter(db):
    project = create_project(db, project_setting=ready_project_setting())
    _create_preparation_assets(db, project)
    service = create_chapter_content_service()

    result = service.save_chapter_draft(
        db,
        project.id,
        1,
        ChapterSaveDTO(
            title="第一章 逃亡夜",
            content_text="林渊连夜逃离宗门，身后追兵已至。",
            change_summary="初版正文",
        ),
    )

    chapters = service.list_chapters(db, project.id)

    assert result.chapter_number == 1
    assert result.current_version_number == 1
    assert result.status == "draft"
    assert result.content_text.startswith("林渊连夜")
    assert [item.chapter_number for item in chapters] == [1]


def test_save_chapter_draft_requires_approved_preparation_assets(db):
    project = create_project(db, project_setting=ready_project_setting())
    service = create_chapter_content_service()

    try:
        service.save_chapter_draft(
            db,
            project.id,
            1,
            ChapterSaveDTO(title="第一章", content_text="正文草稿"),
        )
    except BusinessRuleError as exc:
        assert "outline 必须先确认后才能继续" in exc.message
    else:
        raise AssertionError("expected BusinessRuleError")


def test_editing_old_chapter_marks_only_later_approved_chapters_stale(db):
    project = create_project(db, project_setting=ready_project_setting())
    _create_preparation_assets(db, project)
    service = create_chapter_content_service()
    chapter1 = _create_chapter(db, project, 1, "第一章", "第一章正文", status="approved")
    chapter2 = _create_chapter(db, project, 2, "第二章", "第二章正文", status="approved")
    chapter3 = _create_chapter(db, project, 3, "第三章", "第三章正文", status="approved")
    chapter4 = _create_chapter(db, project, 4, "第四章", "第四章正文", status="draft")

    result = service.save_chapter_draft(
        db,
        project.id,
        2,
        ChapterSaveDTO(title="第二章", content_text="第二章重写版"),
    )

    db.refresh(chapter1)
    db.refresh(chapter2)
    db.refresh(chapter3)
    db.refresh(chapter4)

    assert result.current_version_number == 2
    assert chapter1.status == "approved"
    assert chapter2.status == "draft"
    assert chapter3.status == "stale"
    assert chapter4.status == "draft"


def test_rollback_version_creates_new_current_version(db):
    project = create_project(db, project_setting=ready_project_setting())
    _create_preparation_assets(db, project)
    service = create_chapter_content_service()
    chapter = _create_chapter(db, project, 5, "第五章", "初版正文", status="approved")
    db.refresh(chapter)
    _version_by_number(chapter, 1).is_current = False
    db.commit()
    create_content_version(
        db,
        content=chapter,
        version_number=2,
        content_text="第二版正文",
        is_current=True,
        change_summary="重写",
    )

    result = service.rollback_version(db, project.id, 5, 1)
    versions = service.list_versions(db, project.id, 5)

    assert result.current_version_number == 3
    assert result.content_text == "初版正文"
    assert [item.version_number for item in versions] == [3, 2, 1]
    assert versions[0].is_current is True
    assert versions[1].is_current is False
    assert versions[2].is_current is False


def test_mark_best_version_replaces_previous_best_and_can_be_cleared(db):
    project = create_project(db, project_setting=ready_project_setting())
    _create_preparation_assets(db, project)
    service = create_chapter_content_service()
    chapter = _create_chapter(db, project, 6, "第六章", "初版正文")
    db.refresh(chapter)
    _version_by_number(chapter, 1).is_current = False
    db.commit()
    create_content_version(
        db,
        content=chapter,
        version_number=2,
        content_text="第二版正文",
        is_current=True,
    )

    service.mark_best_version(db, project.id, 6, 1)
    marked = service.mark_best_version(db, project.id, 6, 2)
    cleared = service.clear_best_version(db, project.id, 6, 2)
    versions = service.list_versions(db, project.id, 6)

    assert marked.version_number == 2
    assert marked.is_best is True
    assert cleared.is_best is False
    assert [item.version_number for item in versions if item.is_best] == []


def test_approve_chapter_completes_only_waiting_confirm_task_for_same_content(db):
    project = create_project(db, project_setting=ready_project_setting())
    _create_preparation_assets(db, project)
    service = create_chapter_content_service()
    chapter = _create_chapter(db, project, 1, "第一章", "第一章正文")
    workflow = create_workflow(db, project=project, status="running")
    task = create_chapter_task(
        db,
        workflow=workflow,
        chapter_number=1,
        status="generating",
        content_id=chapter.id,
    )

    result = service.approve_chapter(db, project.id, 1)

    db.refresh(task)
    assert result.status == "approved"
    assert task.status == "completed"
    assert task.content_id == chapter.id


def test_approve_chapter_does_not_complete_non_matching_active_task(db):
    project = create_project(db, project_setting=ready_project_setting())
    other_project = create_project(db, project_setting=ready_project_setting())
    _create_preparation_assets(db, project)
    service = create_chapter_content_service()
    _create_chapter(db, project, 1, "第一章", "第一章正文")
    other_content = create_content(
        db,
        project=other_project,
        chapter_number=1,
        title="外部章节",
        status="approved",
    )
    create_content_version(
        db,
        content=other_content,
        version_number=1,
        content_text="外部正文",
        is_current=True,
    )
    workflow = create_workflow(db, project=project, status="running")
    task = create_chapter_task(
        db,
        workflow=workflow,
        chapter_number=1,
        status="generating",
        content_id=other_content.id,
    )

    result = service.approve_chapter(db, project.id, 1)

    db.refresh(task)
    assert result.status == "approved"
    assert task.status == "generating"
    assert task.content_id == other_content.id


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
