from __future__ import annotations

from pathlib import Path
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.observability.service import AuditLogService

from .dto import ProjectDetailDTO
from .project_deletion_support import (
    PROJECT_DELETE_EVENT,
    PROJECT_RESTORE_EVENT,
    build_project_cleanup_statements,
    cleanup_project_export_directory,
    ensure_project_is_soft_deleted,
    mark_project_deleted,
    record_project_audit,
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
        ensure_project_is_soft_deleted(project)
        try:
            for statement in build_project_cleanup_statements(project.id):
                await db.execute(statement)
            await db.delete(project)
            await db.flush()
            await db.commit()
            cleanup_project_export_directory(self.export_root, project.id)
        except Exception:
            await db.rollback()
            raise
