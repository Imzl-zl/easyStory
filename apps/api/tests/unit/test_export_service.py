from __future__ import annotations

import asyncio
import shutil
import uuid
from pathlib import Path

import pytest

from app.modules.export.service import ExportService
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


def test_export_workflow_uses_only_current_workflow_tasks_and_relative_paths(db):
    project = create_project(db, project_setting=ready_project_setting())
    workflow = create_workflow(db, project=project, status="running")
    chapter = _create_chapter(db, project, 1, "第一章", "第一章导出正文", status="approved")
    _create_chapter(db, project, 99, "外部章节", "不应被导出", status="approved")
    create_chapter_task(
        db,
        workflow=workflow,
        chapter_number=1,
        status="completed",
        content_id=chapter.id,
    )
    create_chapter_task(
        db,
        workflow=workflow,
        chapter_number=2,
        status="skipped",
        title="第二章",
        brief="跳过章节",
    )
    export_root = _build_export_root()
    service = ExportService(export_root)

    try:
        first_exports = asyncio.run(service.export_workflow(async_db(db), workflow, formats=["txt"]))
        db.commit()
        first_path = export_root / Path(first_exports[0].file_path)
        first_text = first_path.read_text(encoding="utf-8")

        second_exports = asyncio.run(service.export_workflow(async_db(db), workflow, formats=["txt"]))
        db.commit()
        second_path = export_root / Path(second_exports[0].file_path)

        assert first_path.exists()
        assert second_path.exists()
        assert not Path(first_exports[0].file_path).is_absolute()
        assert first_exports[0].filename != second_exports[0].filename
        assert "第一章导出正文" in first_text
        assert "不应被导出" not in first_text
    finally:
        shutil.rmtree(export_root, ignore_errors=True)


def test_export_workflow_blocks_generating_task(db):
    project = create_project(db, project_setting=ready_project_setting())
    workflow = create_workflow(db, project=project, status="running")
    chapter = _create_chapter(db, project, 1, "第一章", "第一章导出正文", status="approved")
    create_chapter_task(
        db,
        workflow=workflow,
        chapter_number=1,
        status="generating",
        content_id=chapter.id,
    )
    export_root = _build_export_root()
    service = ExportService(export_root)

    try:
        with pytest.raises(BusinessRuleError, match="正在生成中"):
            asyncio.run(service.export_workflow(async_db(db), workflow, formats=["txt"]))
    finally:
        shutil.rmtree(export_root, ignore_errors=True)


def test_export_workflow_cleans_up_files_when_flush_fails(
    db,
    monkeypatch,
):
    project = create_project(db, project_setting=ready_project_setting())
    workflow = create_workflow(db, project=project, status="running")
    chapter = _create_chapter(db, project, 1, "第一章", "第一章导出正文", status="approved")
    create_chapter_task(
        db,
        workflow=workflow,
        chapter_number=1,
        status="completed",
        content_id=chapter.id,
    )
    export_root = _build_export_root()
    service = ExportService(export_root)

    def failing_flush():
        raise RuntimeError("flush failed")

    monkeypatch.setattr(db, "flush", failing_flush)

    try:
        with pytest.raises(RuntimeError, match="flush failed"):
            asyncio.run(service.export_workflow(async_db(db), workflow, formats=["txt"]))
        db.rollback()
        assert list(export_root.rglob("*.txt")) == []
    finally:
        shutil.rmtree(export_root, ignore_errors=True)


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


def _build_export_root() -> Path:
    return Path.cwd() / ".pytest-exports" / f"export-service-{uuid.uuid4().hex}"
