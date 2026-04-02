from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.content.models import Content
from app.modules.project.models import Project
from app.modules.workflow.models import ChapterTask, WorkflowExecution
from app.modules.workflow.service.snapshot_support import workflow_to_summary_dto
from app.shared.runtime.errors import BusinessRuleError, NotFoundError

from .dto import (
    PreparationAssetStatusDTO,
    PreparationChapterTaskCountsDTO,
    PreparationChapterTaskStatusDTO,
    PreparationNextStep,
    ProjectDocumentDTO,
    ProjectDocumentSaveDTO,
    ProjectPreparationStatusDTO,
    ProjectSettingSnapshotDTO,
    ProjectSettingUpdateDTO,
    SettingCompletenessResultDTO,
)
from .project_document_support import (
    CHAPTER_PLAN_DOCUMENT_PATH,
    OPENING_PLAN_DOCUMENT_PATH,
    OUTLINE_DOCUMENT_PATH,
    build_chapter_plan_document,
    build_setting_document_seed,
    is_canonical_project_document_path,
    parse_chapter_number_from_document_path,
)
from .project_service_support import (
    CHAPTER_TASK_STALE_STATUS,
    build_setting_impact_summary,
    build_project_statement,
    count_chapter_tasks,
    current_version,
    ensure_setting_allows_preparation,
    evaluate_setting,
    mark_related_content_stale,
    resolve_asset_step_status,
    resolve_chapter_task_step_status,
    to_snapshot,
)

if TYPE_CHECKING:
    from app.modules.project.infrastructure import ProjectDocumentFileStore


class ProjectService:
    def __init__(self, *, document_file_store: "ProjectDocumentFileStore | None" = None) -> None:
        self.document_file_store = document_file_store

    async def require_project(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None = None,
        include_deleted: bool = False,
        load_contents: bool = False,
        load_template: bool = False,
    ) -> Project:
        project = await db.scalar(
            build_project_statement(
                project_id,
                owner_id=owner_id,
                include_deleted=include_deleted,
                load_contents=load_contents,
                load_template=load_template,
            )
        )
        if project is None:
            raise NotFoundError(f"Project not found: {project_id}")
        return project

    async def update_project_setting(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        payload: ProjectSettingUpdateDTO,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ProjectSettingSnapshotDTO:
        project = await self.require_project(
            db,
            project_id,
            owner_id=owner_id,
            load_contents=True,
        )
        setting_dict = payload.project_setting.model_dump(exclude_none=True)
        if project.project_setting == setting_dict:
            return to_snapshot(project)
        project.project_setting = setting_dict
        content_impacts = mark_related_content_stale(project)
        stale_chapter_task_count = await self._mark_chapter_tasks_stale(db, project.id)
        impact = build_setting_impact_summary(
            content_impacts,
            stale_chapter_task_count=stale_chapter_task_count,
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return to_snapshot(project, impact=impact)

    async def get_project_document(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        document_path: str,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ProjectDocumentDTO:
        project = await self.require_project(db, project_id, owner_id=owner_id)
        if self.document_file_store is not None and not is_canonical_project_document_path(document_path):
            record = self.document_file_store.find_project_document(project.id, document_path)
            if record is not None:
                return ProjectDocumentDTO(
                    project_id=project.id,
                    path=document_path,
                    content=record.content,
                    source="file",
                    updated_at=record.updated_at,
                )
        content, source = await self._load_project_document_seed(db, project, document_path)
        return ProjectDocumentDTO(
            project_id=project.id,
            path=document_path,
            content=content,
            source=source,
            updated_at=None,
        )

    async def save_project_document(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        document_path: str,
        payload: ProjectDocumentSaveDTO,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ProjectDocumentDTO:
        project = await self.require_project(db, project_id, owner_id=owner_id)
        if self.document_file_store is None:
            raise RuntimeError("Project document file store is not configured")
        if is_canonical_project_document_path(document_path):
            raise BusinessRuleError("该文稿属于正式内容真值，请通过大纲或正文保存链路更新")
        record = self.document_file_store.save_project_document(project.id, document_path, payload.content)
        return ProjectDocumentDTO(
            project_id=project.id,
            path=document_path,
            content=record.content,
            source="file",
            updated_at=record.updated_at,
        )

    async def check_setting_completeness(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> SettingCompletenessResultDTO:
        project = await self.require_project(db, project_id, owner_id=owner_id)
        return evaluate_setting(project)

    def ensure_setting_allows_preparation(self, project: Project) -> SettingCompletenessResultDTO:
        return ensure_setting_allows_preparation(project)

    async def get_preparation_status(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None = None,
    ) -> ProjectPreparationStatusDTO:
        project = await self.require_project(db, project_id, owner_id=owner_id)
        setting = evaluate_setting(project)
        outline = await self._get_asset_status(db, project.id, "outline")
        opening_plan = await self._get_asset_status(db, project.id, "opening_plan")
        active_workflow = await self._find_active_workflow(db, project.id)
        relevant_workflow = active_workflow or await self._find_latest_workflow(db, project.id)
        chapter_tasks = await self._get_chapter_task_status(
            db,
            relevant_workflow.id if relevant_workflow is not None else None,
        )
        can_start_workflow = self._can_start_workflow(setting, outline, opening_plan, active_workflow)
        next_step, next_step_detail = self._resolve_next_step(
            setting,
            outline,
            opening_plan,
            chapter_tasks,
            active_workflow,
        )
        return ProjectPreparationStatusDTO(
            project_id=project.id,
            setting=setting,
            outline=outline,
            opening_plan=opening_plan,
            chapter_tasks=chapter_tasks,
            active_workflow=(
                workflow_to_summary_dto(active_workflow) if active_workflow is not None else None
            ),
            can_start_workflow=can_start_workflow,
            next_step=next_step,
            next_step_detail=next_step_detail,
        )

    async def _mark_chapter_tasks_stale(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> int:
        tasks = (await db.scalars(select(ChapterTask).where(ChapterTask.project_id == project_id))).all()
        updated_count = 0
        for task in tasks:
            if task.status == CHAPTER_TASK_STALE_STATUS:
                continue
            task.status = CHAPTER_TASK_STALE_STATUS
            updated_count += 1
        return updated_count

    async def _get_asset_status(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        content_type: str,
    ) -> PreparationAssetStatusDTO:
        content = await db.scalar(
            select(Content)
            .options(selectinload(Content.versions))
            .where(
                Content.project_id == project_id,
                Content.content_type == content_type,
            )
        )
        if content is None:
            return PreparationAssetStatusDTO(
                content_id=None,
                step_status="not_started",
                content_status=None,
                version_number=None,
                has_content=False,
                updated_at=None,
            )
        version = current_version(content)
        has_content = bool(version and version.content_text.strip())
        return PreparationAssetStatusDTO(
            content_id=content.id,
            step_status=resolve_asset_step_status(content, has_content),
            content_status=content.status,
            version_number=version.version_number if version is not None else None,
            has_content=has_content,
            updated_at=content.updated_at,
        )

    async def _find_active_workflow(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> WorkflowExecution | None:
        return await db.scalar(
            select(WorkflowExecution).where(
                WorkflowExecution.project_id == project_id,
                WorkflowExecution.status.in_(("created", "running", "paused")),
            )
        )

    async def _find_latest_workflow(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> WorkflowExecution | None:
        return await db.scalar(
            select(WorkflowExecution)
            .where(WorkflowExecution.project_id == project_id)
            .order_by(
                WorkflowExecution.updated_at.desc(),
                WorkflowExecution.completed_at.desc().nulls_last(),
                WorkflowExecution.started_at.desc().nulls_last(),
                WorkflowExecution.created_at.desc(),
                WorkflowExecution.id.desc(),
            )
            .limit(1)
        )

    async def _get_chapter_task_status(
        self,
        db: AsyncSession,
        workflow_execution_id: uuid.UUID | None,
    ) -> PreparationChapterTaskStatusDTO:
        if workflow_execution_id is None:
            return PreparationChapterTaskStatusDTO(
                workflow_execution_id=None,
                step_status="not_started",
                total=0,
                counts=PreparationChapterTaskCountsDTO(),
            )
        tasks = (
            await db.scalars(
                select(ChapterTask).where(ChapterTask.workflow_execution_id == workflow_execution_id)
            )
        ).all()
        counts = count_chapter_tasks(tasks)
        return PreparationChapterTaskStatusDTO(
            workflow_execution_id=workflow_execution_id,
            step_status=resolve_chapter_task_step_status(counts),
            total=len(tasks),
            counts=counts,
        )

    async def _load_project_document_seed(
        self,
        db: AsyncSession,
        project: Project,
        document_path: str,
    ) -> tuple[str, str]:
        if document_path == OUTLINE_DOCUMENT_PATH:
            return await self._load_story_asset_seed(db, project.id, "outline"), "outline"
        if document_path == OPENING_PLAN_DOCUMENT_PATH:
            return await self._load_story_asset_seed(db, project.id, "opening_plan"), "opening_plan"
        if document_path == CHAPTER_PLAN_DOCUMENT_PATH:
            return await self._load_chapter_plan_seed(db, project.id), "chapter_plan"
        chapter_number = parse_chapter_number_from_document_path(document_path)
        if chapter_number is not None:
            return await self._load_chapter_seed(db, project.id, chapter_number), "chapter"
        setting_document = build_setting_document_seed(project.project_setting, document_path)
        if setting_document:
            return setting_document, "setting_summary"
        return "", "empty"

    async def _load_story_asset_seed(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        content_type: str,
    ) -> str:
        content = await db.scalar(
            select(Content)
            .options(selectinload(Content.versions))
            .where(Content.project_id == project_id, Content.content_type == content_type)
        )
        version = current_version(content) if content is not None else None
        return version.content_text if version is not None else ""

    async def _load_chapter_seed(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        chapter_number: int,
    ) -> str:
        content = await db.scalar(
            select(Content)
            .options(selectinload(Content.versions))
            .where(
                Content.project_id == project_id,
                Content.content_type == "chapter",
                Content.chapter_number == chapter_number,
            )
        )
        version = current_version(content) if content is not None else None
        return version.content_text if version is not None else ""

    async def _load_chapter_plan_seed(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> str:
        chapters = (
            await db.scalars(
                select(Content)
                .where(
                    Content.project_id == project_id,
                    Content.content_type == "chapter",
                )
                .order_by(Content.chapter_number.asc(), Content.id.asc())
            )
        ).all()
        return build_chapter_plan_document(chapters)

    def _can_start_workflow(
        self,
        setting: SettingCompletenessResultDTO,
        outline: PreparationAssetStatusDTO,
        opening_plan: PreparationAssetStatusDTO,
        active_workflow: WorkflowExecution | None,
    ) -> bool:
        del setting
        return (
            outline.step_status == "approved"
            and opening_plan.step_status == "approved"
            and active_workflow is None
        )

    def _resolve_next_step(
        self,
        setting: SettingCompletenessResultDTO,
        outline: PreparationAssetStatusDTO,
        opening_plan: PreparationAssetStatusDTO,
        chapter_tasks: PreparationChapterTaskStatusDTO,
        active_workflow: WorkflowExecution | None,
    ) -> tuple[PreparationNextStep, str]:
        if outline.step_status != "approved":
            return "outline", "需要先生成并确认大纲"
        if opening_plan.step_status != "approved":
            return "opening_plan", "需要先生成并确认开篇设计"
        if chapter_tasks.step_status == "stale" and active_workflow is not None:
            return "chapter_tasks", "当前章节计划已失效，需要在现有工作流中重建章节任务"
        if active_workflow is not None:
            return "workflow", "当前已有活跃工作流，可继续推进章节任务或正文生成"
        if chapter_tasks.step_status == "completed":
            return "chapter", "章节计划已就绪，可继续推进正文生成与确认"
        if setting.issues:
            return "workflow", "结构化摘要还有可补充项，但这不会阻塞继续生成大纲、开篇或正文。"
        return "workflow", "前置资产已就绪，可以启动工作流"
