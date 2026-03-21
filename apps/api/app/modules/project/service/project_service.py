from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.project.models import Project
from app.modules.workflow.models import ChapterTask
from app.shared.runtime.errors import NotFoundError

from .dto import ProjectSettingSnapshotDTO, ProjectSettingUpdateDTO, SettingCompletenessResultDTO
from .project_service_support import (
    CHAPTER_TASK_STALE_STATUS,
    build_project_statement,
    ensure_setting_allows_preparation,
    evaluate_setting,
    mark_related_content_stale,
    to_snapshot,
)


class ProjectService:
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
        mark_related_content_stale(project)
        await self._mark_chapter_tasks_stale(db, project.id)
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return to_snapshot(project)

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

    async def _mark_chapter_tasks_stale(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> None:
        tasks = (await db.scalars(select(ChapterTask).where(ChapterTask.project_id == project_id))).all()
        for task in tasks:
            if task.status != CHAPTER_TASK_STALE_STATUS:
                task.status = CHAPTER_TASK_STALE_STATUS
