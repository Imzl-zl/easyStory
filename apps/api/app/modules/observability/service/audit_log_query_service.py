from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.credential.models import ModelCredential
from app.modules.project.models import Project
from app.shared.runtime.errors import NotFoundError

from .audit_log_query_support import (
    build_credential_audit_log_statement,
    build_project_audit_log_statement,
    normalize_event_type_filter,
    to_audit_log_view,
)
from .dto import AuditLogViewDTO

USER_CREDENTIAL_OWNER_TYPE = "user"
PROJECT_CREDENTIAL_OWNER_TYPE = "project"


class AuditLogQueryService:
    async def list_project_audit_logs(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[AuditLogViewDTO]:
        await self._require_owned_project(db, project_id, owner_id=owner_id)
        normalized_event_type = normalize_event_type_filter(event_type)
        statement = build_project_audit_log_statement(
            project_id,
            event_type=normalized_event_type,
        ).limit(limit)
        audit_logs = (await db.scalars(statement)).all()
        return [to_audit_log_view(item) for item in audit_logs]

    async def list_credential_audit_logs(
        self,
        db: AsyncSession,
        credential_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[AuditLogViewDTO]:
        await self._require_owned_credential(db, credential_id, owner_id=owner_id)
        normalized_event_type = normalize_event_type_filter(event_type)
        statement = build_credential_audit_log_statement(
            credential_id,
            event_type=normalized_event_type,
        ).limit(limit)
        audit_logs = (await db.scalars(statement)).all()
        return [to_audit_log_view(item) for item in audit_logs]

    async def _require_owned_project(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> None:
        project_id_result = await db.scalar(
            select(Project.id).where(
                Project.id == project_id,
                Project.owner_id == owner_id,
            )
        )
        if project_id_result is None:
            raise NotFoundError(f"Project not found: {project_id}")

    async def _require_owned_credential(
        self,
        db: AsyncSession,
        credential_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> None:
        credential = await db.scalar(
            select(ModelCredential).where(ModelCredential.id == credential_id)
        )
        if credential is None:
            raise NotFoundError(f"Credential not found: {credential_id}")
        if credential.owner_type == USER_CREDENTIAL_OWNER_TYPE and credential.owner_id == owner_id:
            return
        if credential.owner_type != PROJECT_CREDENTIAL_OWNER_TYPE:
            raise NotFoundError(f"Credential not found: {credential_id}")
        project_id_result = await db.scalar(
            select(Project.id).where(
                Project.id == credential.owner_id,
                Project.owner_id == owner_id,
            )
        )
        if project_id_result is None:
            raise NotFoundError(f"Credential not found: {credential_id}")
