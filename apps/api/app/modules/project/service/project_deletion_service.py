from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.observability.service import AuditLogService
from app.modules.project.models import Project

from .dto import ProjectDetailDTO, ProjectTrashCleanupResultDTO
from .project_deletion_support import (
    DEFAULT_PROJECT_TRASH_BATCH_SIZE,
    DEFAULT_PROJECT_TRASH_RETENTION_DAYS,
    PROJECT_DELETE_EVENT,
    PROJECT_RESTORE_EVENT,
    build_deleted_project_statement,
    build_project_cleanup_statements,
    cleanup_project_export_directory,
    ensure_project_is_soft_deleted,
    mark_project_deleted,
    record_project_audit,
    resolve_project_trash_cutoff,
    restore_project_from_trash,
)
from .project_service import ProjectService


class ProjectDeletionService:
    def __init__(
        self,
        project_service: ProjectService,
        audit_log_service: AuditLogService,
        export_root: Path,
    ) -> None:
        self.project_service = project_service
        self.audit_log_service = audit_log_service
        self.export_root = export_root

    async def soft_delete_project(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> ProjectDetailDTO:
        project = await self.project_service.require_project(db, project_id, owner_id=owner_id)
        mark_project_deleted(project)
        record_project_audit(
            self.audit_log_service,
            db,
            actor_user_id=owner_id,
            event_type=PROJECT_DELETE_EVENT,
            project=project,
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return ProjectDetailDTO.model_validate(project, from_attributes=True)

    async def restore_project(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> ProjectDetailDTO:
        project = await self.project_service.require_project(
            db,
            project_id,
            owner_id=owner_id,
            include_deleted=True,
        )
        restore_project_from_trash(project)
        record_project_audit(
            self.audit_log_service,
            db,
            actor_user_id=owner_id,
            event_type=PROJECT_RESTORE_EVENT,
            project=project,
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return ProjectDetailDTO.model_validate(project, from_attributes=True)

    async def physical_delete_project(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> None:
        project = await self.project_service.require_project(
            db,
            project_id,
            owner_id=owner_id,
            include_deleted=True,
        )
        await self._physically_delete_loaded_project(db, project)

    async def empty_trash(
        self,
        db: AsyncSession,
        *,
        owner_id: uuid.UUID,
    ) -> ProjectTrashCleanupResultDTO:
        projects = await self._list_deleted_projects(db, owner_id=owner_id)
        return await self._cleanup_projects(db, projects)

    async def cleanup_expired_projects(
        self,
        db: AsyncSession,
        *,
        now: datetime | None = None,
        owner_id: uuid.UUID | None = None,
        retention_days: int = DEFAULT_PROJECT_TRASH_RETENTION_DAYS,
        batch_size: int = DEFAULT_PROJECT_TRASH_BATCH_SIZE,
    ) -> ProjectTrashCleanupResultDTO:
        cutoff = resolve_project_trash_cutoff(
            now or datetime.now(UTC),
            retention_days=retention_days,
        )
        projects = await self._list_deleted_projects(
            db,
            owner_id=owner_id,
            deleted_before=cutoff,
            limit=batch_size,
        )
        return await self._cleanup_projects(db, projects)

    async def _list_deleted_projects(
        self,
        db: AsyncSession,
        *,
        owner_id: uuid.UUID | None,
        deleted_before: datetime | None = None,
        limit: int | None = None,
    ) -> list[Project]:
        statement = build_deleted_project_statement(
            owner_id=owner_id,
            deleted_before=deleted_before,
            limit=limit,
        )
        return list((await db.scalars(statement)).all())

    async def _cleanup_projects(
        self,
        db: AsyncSession,
        projects: list[Project],
    ) -> ProjectTrashCleanupResultDTO:
        deleted_count = 0
        for project in projects:
            await self._physically_delete_loaded_project(db, project)
            deleted_count += 1
        return ProjectTrashCleanupResultDTO(deleted_count=deleted_count)

    async def _physically_delete_loaded_project(
        self,
        db: AsyncSession,
        project: Project,
    ) -> None:
        ensure_project_is_soft_deleted(project)
        try:
            for statement in build_project_cleanup_statements(project.id):
                await db.execute(statement)
            await db.delete(project)
            await db.flush()
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        cleanup_project_export_directory(self.export_root, project.id)
