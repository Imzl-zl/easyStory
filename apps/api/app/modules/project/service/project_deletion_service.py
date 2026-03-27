from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.observability.service import AuditLogService
from app.modules.project.models import Project

from .dto import (
    ProjectDetailDTO,
    ProjectTrashCleanupFailureDTO,
    ProjectTrashCleanupResultDTO,
)
from .project_deletion_support import (
    DEFAULT_PROJECT_TRASH_BATCH_SIZE,
    DEFAULT_PROJECT_TRASH_RETENTION_DAYS,
    PROJECT_DELETE_EVENT,
    PROJECT_RESTORE_EVENT,
    build_deleted_project_id_statement,
    build_project_cleanup_statements,
    build_soft_deleted_project_statement,
    cleanup_project_export_directory,
    ensure_project_is_soft_deleted,
    ensure_positive_project_trash_value,
    mark_project_deleted,
    record_project_audit,
    resolve_project_trash_cutoff,
    restore_project_from_trash,
)
from .project_service import ProjectService


@dataclass(slots=True)
class _CleanupAccumulator:
    deleted_count: int = 0
    skipped_project_ids: list[uuid.UUID] = field(default_factory=list)
    failed_items: list[ProjectTrashCleanupFailureDTO] = field(default_factory=list)

    def build_result(self) -> ProjectTrashCleanupResultDTO:
        return ProjectTrashCleanupResultDTO(
            deleted_count=self.deleted_count,
            skipped_count=len(self.skipped_project_ids),
            failed_count=len(self.failed_items),
            skipped_project_ids=self.skipped_project_ids,
            failed_items=self.failed_items,
        )


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
        project_ids = await self._list_deleted_project_ids(db, owner_id=owner_id)
        return await self._cleanup_projects(db, project_ids, owner_id=owner_id)

    async def cleanup_expired_projects(
        self,
        db: AsyncSession,
        *,
        now: datetime | None = None,
        owner_id: uuid.UUID | None = None,
        retention_days: int = DEFAULT_PROJECT_TRASH_RETENTION_DAYS,
        batch_size: int = DEFAULT_PROJECT_TRASH_BATCH_SIZE,
    ) -> ProjectTrashCleanupResultDTO:
        retention_days = ensure_positive_project_trash_value(
            retention_days,
            field_name="retention_days",
        )
        batch_size = ensure_positive_project_trash_value(
            batch_size,
            field_name="batch_size",
        )
        cutoff = resolve_project_trash_cutoff(
            now or datetime.now(UTC),
            retention_days=retention_days,
        )
        project_ids = await self._list_deleted_project_ids(
            db,
            owner_id=owner_id,
            deleted_before=cutoff,
            limit=batch_size,
        )
        return await self._cleanup_projects(db, project_ids, owner_id=owner_id)

    async def _list_deleted_project_ids(
        self,
        db: AsyncSession,
        *,
        owner_id: uuid.UUID | None,
        deleted_before: datetime | None = None,
        limit: int | None = None,
    ) -> list[uuid.UUID]:
        statement = build_deleted_project_id_statement(
            owner_id=owner_id,
            deleted_before=deleted_before,
            limit=limit,
        )
        return list((await db.scalars(statement)).all())

    async def _cleanup_projects(
        self,
        db: AsyncSession,
        project_ids: list[uuid.UUID],
        *,
        owner_id: uuid.UUID | None,
    ) -> ProjectTrashCleanupResultDTO:
        result = _CleanupAccumulator()
        for project_id in project_ids:
            await self._cleanup_project_by_id(
                db,
                project_id,
                owner_id=owner_id,
                result=result,
            )
        return result.build_result()

    async def _cleanup_project_by_id(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None,
        result: _CleanupAccumulator,
    ) -> None:
        project = await self._load_soft_deleted_project(db, project_id, owner_id=owner_id)
        if project is None:
            result.skipped_project_ids.append(project_id)
            return
        try:
            await self._physically_delete_loaded_project(db, project)
        except Exception as exc:
            await self._record_cleanup_failure(db, project_id, exc, result)
            return
        result.deleted_count += 1

    async def _load_soft_deleted_project(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None,
    ) -> Project | None:
        statement = build_soft_deleted_project_statement(
            project_id,
            owner_id=owner_id,
        ).with_for_update()
        return await db.scalar(statement)

    async def _record_cleanup_failure(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        exc: Exception,
        result: _CleanupAccumulator,
    ) -> None:
        project_deleted = await self._project_is_missing(db, project_id)
        if project_deleted:
            result.deleted_count += 1
        result.failed_items.append(
            ProjectTrashCleanupFailureDTO(
                project_id=project_id,
                message=self._format_cleanup_failure_message(
                    exc,
                    project_deleted=project_deleted,
                ),
            )
        )

    async def _project_is_missing(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> bool:
        return await db.get(Project, project_id) is None

    def _format_cleanup_failure_message(
        self,
        exc: Exception,
        *,
        project_deleted: bool,
    ) -> str:
        detail = str(exc) or exc.__class__.__name__
        if project_deleted:
            return f"项目已删除，但导出目录清理失败: {detail}"
        return f"项目清理失败: {detail}"

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
