from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.content.models import Content
from app.modules.export.models import Export
from app.modules.project.models import Project
from app.modules.workflow.models import ChapterTask, WorkflowExecution
from app.shared.runtime.errors import BusinessRuleError, NotFoundError

from .dto import ExportViewDTO
from .export_file_support import cleanup_files, resolve_download_path, write_export_file

EXPORT_ROOT_DIR = ".runtime/exports"
EXPORTABLE_CONTENT_STATUSES = frozenset({"approved", "stale"})
BLOCKING_TASK_STATUS_MESSAGES = {
    "pending": "第{chapter_number}章尚未完成，无法导出",
    "generating": "第{chapter_number}章正在生成中，无法导出",
    "interrupted": "第{chapter_number}章已中断，无法导出",
    "failed": "第{chapter_number}章生成失败，无法导出",
}


class ExportService:
    def __init__(self, export_root: Path) -> None:
        self.export_root = export_root

    async def create_workflow_exports(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        formats: list[str],
        owner_id: uuid.UUID,
    ) -> list[Export]:
        workflow = await self._require_owned_workflow(db, workflow_id, owner_id=owner_id)
        exports = await self.export_workflow(
            db,
            workflow,
            formats=formats,
            config_snapshot=workflow.workflow_snapshot,
        )
        await db.commit()
        for export in exports:
            await db.refresh(export)
        return exports

    async def list_project_exports(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> list[Export]:
        await self._require_owned_project(db, project_id, owner_id=owner_id)
        statement = select(Export).where(Export.project_id == project_id)
        return (await db.scalars(statement.order_by(Export.created_at.desc()))).all()

    async def resolve_download(
        self,
        db: AsyncSession,
        export_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> tuple[Export, Path]:
        export = await self._require_owned_export(db, export_id, owner_id=owner_id)
        file_path = resolve_download_path(
            self.export_root,
            export,
            export_id=export_id,
        )
        return export, file_path

    def to_view_dto(self, export: Export) -> ExportViewDTO:
        return ExportViewDTO(
            id=export.id,
            project_id=export.project_id,
            format=export.format,
            filename=export.filename,
            file_size=export.file_size,
            created_at=export.created_at,
        )

    async def export_workflow(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        *,
        formats: list[str],
        config_snapshot: dict | None = None,
    ) -> list[Export]:
        chapters = await self._load_chapters(db, workflow)
        rendered = self._render_current_versions(chapters)
        output_dir = self.export_root / str(workflow.project_id) / str(workflow.id)
        output_dir.mkdir(parents=True, exist_ok=True)
        prepared_exports: list[tuple[Export, Path]] = []
        try:
            for export_format in formats:
                prepared_exports.append(
                    write_export_file(
                        self.export_root,
                        project_id=workflow.project_id,
                        output_dir=output_dir,
                        rendered=rendered,
                        export_format=export_format,
                        config_snapshot=config_snapshot or workflow.workflow_snapshot,
                    )
                )
            exports = [item[0] for item in prepared_exports]
            db.add_all(exports)
            await db.flush()
            return exports
        except Exception:
            cleanup_files([path for _, path in prepared_exports])
            raise

    async def _load_chapters(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
    ) -> list[Content]:
        tasks = (
            await db.scalars(
                select(ChapterTask)
                .where(ChapterTask.workflow_execution_id == workflow.id)
                .order_by(ChapterTask.chapter_number.asc())
            )
        ).all()
        if not tasks:
            raise BusinessRuleError("当前工作流没有章节计划，无法导出")
        content_ids = self._collect_content_ids(tasks)
        contents = (
            await db.scalars(
                select(Content)
                .options(selectinload(Content.versions))
                .where(Content.id.in_(content_ids))
            )
        ).all()
        chapters = self._match_completed_chapters(
            tasks,
            {content.id: content for content in contents},
            workflow.project_id,
        )
        if not chapters:
            raise BusinessRuleError("没有可导出的已完成章节内容")
        return chapters

    def _collect_content_ids(self, tasks: list[ChapterTask]) -> list[uuid.UUID]:
        content_ids: list[uuid.UUID] = []
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
            content_ids.append(task.content_id)
        return content_ids

    def _match_completed_chapters(
        self,
        tasks: list[ChapterTask],
        content_map: dict[uuid.UUID, Content],
        project_id: uuid.UUID,
    ) -> list[Content]:
        chapters: list[Content] = []
        for task in tasks:
            if task.status == "skipped":
                continue
            assert task.content_id is not None
            content = content_map.get(task.content_id)
            if content is None or content.project_id != project_id:
                raise BusinessRuleError(f"第{task.chapter_number}章内容不存在，无法导出")
            if content.content_type != "chapter" or content.chapter_number != task.chapter_number:
                raise BusinessRuleError(f"第{task.chapter_number}章内容绑定不一致，无法导出")
            if content.status not in EXPORTABLE_CONTENT_STATUSES:
                raise BusinessRuleError(
                    f"第{task.chapter_number}章当前状态为 {content.status}，无法导出"
                )
            chapters.append(content)
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

    async def _require_owned_workflow(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowExecution:
        workflow = await db.scalar(
            select(WorkflowExecution)
            .join(Project, WorkflowExecution.project_id == Project.id)
            .where(WorkflowExecution.id == workflow_id, Project.owner_id == owner_id)
        )
        if workflow is None:
            raise NotFoundError(f"Workflow execution not found: {workflow_id}")
        return workflow

    async def _require_owned_project(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> Project:
        project = await db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == owner_id))
        if project is None:
            raise NotFoundError(f"Project not found: {project_id}")
        return project

    async def _require_owned_export(
        self,
        db: AsyncSession,
        export_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> Export:
        export = await db.scalar(
            select(Export)
            .join(Project, Export.project_id == Project.id)
            .where(Export.id == export_id, Project.owner_id == owner_id)
        )
        if export is None:
            raise NotFoundError(f"Export not found: {export_id}")
        return export
