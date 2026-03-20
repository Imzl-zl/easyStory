from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.modules.content.models import Content
from app.modules.export.models import Export
from app.modules.workflow.models import ChapterTask, WorkflowExecution
from app.shared.runtime.errors import BusinessRuleError

EXPORT_ROOT_DIR = ".runtime/exports"
SUPPORTED_EXPORT_FORMATS = frozenset({"txt", "markdown"})
EXPORTABLE_CONTENT_STATUSES = frozenset({"approved", "stale"})
EXPORT_FILENAME_PREFIX = "workflow-export"
EXPORT_FILENAME_TOKEN_LENGTH = 8
BLOCKING_TASK_STATUS_MESSAGES = {
    "pending": "第{chapter_number}章尚未完成，无法导出",
    "generating": "第{chapter_number}章正在生成中，无法导出",
    "interrupted": "第{chapter_number}章已中断，无法导出",
    "failed": "第{chapter_number}章生成失败，无法导出",
}


class ExportService:
    def __init__(self, export_root: Path) -> None:
        self.export_root = export_root

    def export_workflow(
        self,
        db: Session,
        workflow: WorkflowExecution,
        *,
        formats: list[str],
        config_snapshot: dict | None = None,
    ) -> list[Export]:
        chapters = self._load_chapters(db, workflow)
        rendered = self._render_current_versions(chapters)
        output_dir = self.export_root / str(workflow.project_id) / str(workflow.id)
        output_dir.mkdir(parents=True, exist_ok=True)
        prepared_exports: list[tuple[Export, Path]] = []
        try:
            for export_format in formats:
                prepared_exports.append(
                    self._write_export(
                        workflow.project_id,
                        output_dir,
                        rendered,
                        export_format,
                        config_snapshot,
                    )
                )
            exports = [item[0] for item in prepared_exports]
            db.add_all(exports)
            db.flush()
            return exports
        except Exception:
            self._cleanup_files([path for _, path in prepared_exports])
            raise

    def _load_chapters(
        self,
        db: Session,
        workflow: WorkflowExecution,
    ) -> list[Content]:
        tasks = (
            db.query(ChapterTask)
            .filter(ChapterTask.workflow_execution_id == workflow.id)
            .order_by(ChapterTask.chapter_number.asc())
            .all()
        )
        if not tasks:
            raise BusinessRuleError("当前工作流没有章节计划，无法导出")
        chapters: list[Content] = []
        for task in tasks:
            if task.status == "skipped":
                continue
            if task.status != "completed":
                raise BusinessRuleError(
                    BLOCKING_TASK_STATUS_MESSAGES.get(
                        task.status,
                        f"第{task.chapter_number}章状态异常，无法导出",
                    ).format(chapter_number=task.chapter_number)
                )
            if task.content_id is None:
                raise BusinessRuleError(f"第{task.chapter_number}章缺少已确认正文，无法导出")
            content = db.get(Content, task.content_id)
            if content is None or content.project_id != workflow.project_id:
                raise BusinessRuleError(f"第{task.chapter_number}章内容不存在，无法导出")
            if content.content_type != "chapter" or content.chapter_number != task.chapter_number:
                raise BusinessRuleError(f"第{task.chapter_number}章内容绑定不一致，无法导出")
            if content.status not in EXPORTABLE_CONTENT_STATUSES:
                raise BusinessRuleError(
                    f"第{task.chapter_number}章当前状态为 {content.status}，无法导出"
                )
            chapters.append(content)
        if not chapters:
            raise BusinessRuleError("没有可导出的已完成章节内容")
        return chapters

    def _render_current_versions(
        self,
        chapters: list[Content],
    ) -> list[tuple[Content, str]]:
        rendered: list[tuple[Content, str]] = []
        for chapter in chapters:
            current_version = next((item for item in chapter.versions if item.is_current), None)
            if current_version is None or not current_version.content_text.strip():
                raise BusinessRuleError(f"第{chapter.chapter_number}章缺少当前正文，无法导出")
            rendered.append((chapter, current_version.content_text.strip()))
        return rendered

    def _write_export(
        self,
        project_id: uuid.UUID,
        output_dir: Path,
        rendered: list[tuple[Content, str]],
        export_format: str,
        config_snapshot: dict | None,
    ) -> tuple[Export, Path]:
        if export_format not in SUPPORTED_EXPORT_FORMATS:
            raise BusinessRuleError(f"暂不支持导出格式: {export_format}")
        suffix = "md" if export_format == "markdown" else export_format
        filename = (
            f"{EXPORT_FILENAME_PREFIX}-"
            f"{uuid.uuid4().hex[:EXPORT_FILENAME_TOKEN_LENGTH]}.{suffix}"
        )
        file_path = output_dir / filename
        try:
            file_path.write_text(
                self._render_document(rendered, markdown=export_format == "markdown"),
                encoding="utf-8",
            )
            relative_path = file_path.relative_to(self.export_root).as_posix()
            return (
                Export(
                    project_id=project_id,
                    format=export_format,
                    filename=filename,
                    file_path=relative_path,
                    file_size=file_path.stat().st_size,
                    config_snapshot=config_snapshot,
                ),
                file_path,
            )
        except Exception:
            if file_path.exists():
                file_path.unlink()
            raise

    def _cleanup_files(
        self,
        file_paths: list[Path],
    ) -> None:
        for file_path in file_paths:
            if file_path.exists():
                file_path.unlink()

    def _render_document(
        self,
        rendered: list[tuple[Content, str]],
        *,
        markdown: bool,
    ) -> str:
        blocks = []
        for chapter, text in rendered:
            number = chapter.chapter_number or 0
            heading = f"第{number}章 {chapter.title}"
            if markdown:
                heading = f"# {heading}"
            blocks.append(f"{heading}\n\n{text}")
        return "\n\n".join(blocks).strip() + "\n"
