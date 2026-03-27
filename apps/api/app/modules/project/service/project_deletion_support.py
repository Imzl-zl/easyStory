from __future__ import annotations

import shutil
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analysis.models import Analysis
from app.modules.billing.models import TokenUsage
from app.modules.content.models import Content, ContentVersion
from app.modules.context.models import StoryFact
from app.modules.credential.models import ModelCredential
from app.modules.export.models import Export
from app.modules.observability.models import AuditLog, ExecutionLog, PromptReplay
from app.modules.observability.service import (
    AUDIT_ENTITY_MODEL_CREDENTIAL,
    AUDIT_ENTITY_PROJECT,
    AuditLogService,
)
from app.modules.project.models import Project
from app.modules.review.models import ReviewAction
from app.modules.workflow.models import Artifact, ChapterTask, NodeExecution, WorkflowExecution
from app.shared.runtime.errors import BusinessRuleError

PROJECT_DELETE_EVENT = "project_delete"
PROJECT_RESTORE_EVENT = "project_restore"
PROJECT_CREDENTIAL_OWNER_TYPE = "project"
DEFAULT_PROJECT_TRASH_RETENTION_DAYS = 30
DEFAULT_PROJECT_TRASH_BATCH_SIZE = 100
PHYSICAL_DELETE_REQUIRES_SOFT_DELETE_MESSAGE = (
    "Project must be soft deleted before physical delete"
)


def build_project_cleanup_statements(project_id: uuid.UUID) -> tuple:
    workflow_ids = select(WorkflowExecution.id).where(
        WorkflowExecution.project_id == project_id
    )
    node_ids = select(NodeExecution.id).where(
        NodeExecution.workflow_execution_id.in_(workflow_ids)
    )
    content_ids = select(Content.id).where(Content.project_id == project_id)
    project_credential_ids = select(ModelCredential.id).where(
        ModelCredential.owner_type == PROJECT_CREDENTIAL_OWNER_TYPE,
        ModelCredential.owner_id == project_id,
    )
    return (
        delete(PromptReplay).where(PromptReplay.node_execution_id.in_(node_ids)),
        delete(ExecutionLog).where(
            or_(
                ExecutionLog.workflow_execution_id.in_(workflow_ids),
                ExecutionLog.node_execution_id.in_(node_ids),
            )
        ),
        delete(ReviewAction).where(ReviewAction.node_execution_id.in_(node_ids)),
        delete(Artifact).where(Artifact.node_execution_id.in_(node_ids)),
        delete(TokenUsage).where(
            or_(
                TokenUsage.project_id == project_id,
                TokenUsage.credential_id.in_(project_credential_ids),
            )
        ),
        delete(ChapterTask).where(ChapterTask.project_id == project_id),
        delete(StoryFact).where(StoryFact.project_id == project_id),
        delete(Export).where(Export.project_id == project_id),
        delete(AuditLog).where(
            AuditLog.entity_type == AUDIT_ENTITY_PROJECT,
            AuditLog.entity_id == project_id,
        ),
        delete(AuditLog).where(
            AuditLog.entity_type == AUDIT_ENTITY_MODEL_CREDENTIAL,
            AuditLog.entity_id.in_(project_credential_ids),
        ),
        delete(ContentVersion).where(ContentVersion.content_id.in_(content_ids)),
        delete(Analysis).where(Analysis.project_id == project_id),
        delete(NodeExecution).where(NodeExecution.workflow_execution_id.in_(workflow_ids)),
        delete(WorkflowExecution).where(WorkflowExecution.project_id == project_id),
        delete(Content).where(Content.project_id == project_id),
        delete(ModelCredential).where(ModelCredential.id.in_(project_credential_ids)),
    )


def cleanup_project_export_directory(
    export_root: Path,
    project_id: uuid.UUID,
) -> None:
    resolved_root = export_root.resolve()
    project_export_dir = (export_root / str(project_id)).resolve()
    if not project_export_dir.is_relative_to(resolved_root):
        raise BusinessRuleError("Project export path escaped export root")
    if project_export_dir.exists():
        shutil.rmtree(project_export_dir)


def mark_project_deleted(project: Project) -> None:
    project.deleted_at = datetime.now(UTC)


def restore_project_from_trash(project: Project) -> None:
    if project.deleted_at is None:
        raise BusinessRuleError("Project is not deleted")
    project.deleted_at = None


def ensure_project_is_soft_deleted(project: Project) -> None:
    if project.deleted_at is None:
        raise BusinessRuleError(PHYSICAL_DELETE_REQUIRES_SOFT_DELETE_MESSAGE)


def ensure_positive_project_trash_value(value: int, *, field_name: str) -> int:
    if value <= 0:
        raise BusinessRuleError(f"{field_name} must be greater than 0")
    return value


def _apply_deleted_project_filters(
    statement,
    *,
    owner_id: uuid.UUID | None,
    deleted_before: datetime | None = None,
    limit: int | None = None,
):
    statement = statement.where(Project.deleted_at.is_not(None))
    if owner_id is not None:
        statement = statement.where(Project.owner_id == owner_id)
    if deleted_before is not None:
        statement = statement.where(Project.deleted_at <= deleted_before)
    statement = statement.order_by(Project.deleted_at.asc(), Project.id.asc())
    if limit is not None:
        statement = statement.limit(limit)
    return statement


def build_deleted_project_statement(
    *,
    owner_id: uuid.UUID | None,
    deleted_before: datetime | None = None,
    limit: int | None = None,
):
    statement = select(Project)
    return _apply_deleted_project_filters(
        statement,
        owner_id=owner_id,
        deleted_before=deleted_before,
        limit=limit,
    )


def build_deleted_project_id_statement(
    *,
    owner_id: uuid.UUID | None,
    deleted_before: datetime | None = None,
    limit: int | None = None,
):
    statement = select(Project.id)
    return _apply_deleted_project_filters(
        statement,
        owner_id=owner_id,
        deleted_before=deleted_before,
        limit=limit,
    )


def build_soft_deleted_project_statement(
    project_id: uuid.UUID,
    *,
    owner_id: uuid.UUID | None,
):
    statement = select(Project).where(
        Project.id == project_id,
        Project.deleted_at.is_not(None),
    )
    if owner_id is not None:
        statement = statement.where(Project.owner_id == owner_id)
    return statement


def resolve_project_trash_cutoff(
    now: datetime,
    *,
    retention_days: int,
) -> datetime:
    return now - timedelta(days=retention_days)


def record_project_audit(
    audit_log_service: AuditLogService,
    db: AsyncSession,
    *,
    actor_user_id: uuid.UUID,
    event_type: str,
    project: Project,
) -> None:
    audit_log_service.record(
        db,
        actor_user_id=actor_user_id,
        event_type=event_type,
        entity_type=AUDIT_ENTITY_PROJECT,
        entity_id=project.id,
        details={
            "name": project.name,
            "owner_id": str(project.owner_id),
            "deleted_at": project.deleted_at.isoformat() if project.deleted_at else None,
        },
    )
