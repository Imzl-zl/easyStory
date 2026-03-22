from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.models import TokenUsage
from app.modules.credential.models import ModelCredential
from app.modules.project.models import Project
from app.modules.project.service import ProjectService
from app.shared.runtime.errors import BusinessRuleError, ConflictError, NotFoundError

OWNER_TYPE_SYSTEM = "system"
OWNER_TYPE_USER = "user"
OWNER_TYPE_PROJECT = "project"
CREDENTIAL_DELETE_IN_USE_MESSAGE = (
    "Credential cannot be deleted because token usage history exists"
)


@dataclass(frozen=True)
class CredentialScope:
    owner_type: str
    owner_id: uuid.UUID | None


async def resolve_actor_scope(
    db: AsyncSession,
    *,
    actor_user_id: uuid.UUID,
    owner_type: str,
    project_id: uuid.UUID | None,
    project_service: ProjectService,
) -> CredentialScope:
    if owner_type == OWNER_TYPE_USER:
        if project_id is not None:
            raise BusinessRuleError("user scope does not accept project_id")
        return CredentialScope(owner_type=OWNER_TYPE_USER, owner_id=actor_user_id)
    if owner_type != OWNER_TYPE_PROJECT:
        raise BusinessRuleError("system scope is not available via user API")
    if project_id is None:
        raise BusinessRuleError("project scope requires project_id")
    project = await project_service.require_project(db, project_id, owner_id=actor_user_id)
    return CredentialScope(owner_type=OWNER_TYPE_PROJECT, owner_id=project.id)


async def require_actor_credential(
    db: AsyncSession,
    credential_id: uuid.UUID,
    *,
    actor_user_id: uuid.UUID,
    project_service: ProjectService,
) -> ModelCredential:
    credential = await db.scalar(select(ModelCredential).where(ModelCredential.id == credential_id))
    if credential is None:
        raise NotFoundError(f"Credential not found: {credential_id}")
    if credential.owner_type == OWNER_TYPE_USER and credential.owner_id == actor_user_id:
        return credential
    if credential.owner_type != OWNER_TYPE_PROJECT:
        raise NotFoundError(f"Credential not found: {credential_id}")
    await project_service.require_project(db, credential.owner_id, owner_id=actor_user_id)
    return credential


async def ensure_unique_provider(
    db: AsyncSession,
    *,
    scope: CredentialScope,
    provider: str,
) -> None:
    statement = scope_statement(scope).where(ModelCredential.provider == provider)
    if await db.scalar(statement) is not None:
        raise ConflictError(
            f"Credential already exists for provider '{provider}' in scope '{scope.owner_type}'"
        )


async def load_project_if_present(
    db: AsyncSession,
    project_id: uuid.UUID | None,
    *,
    owner_id: uuid.UUID,
    project_service: ProjectService,
) -> Project | None:
    if project_id is None:
        return None
    return await project_service.require_project(db, project_id, owner_id=owner_id)


async def find_active_credential(
    db: AsyncSession,
    *,
    owner_type: str,
    owner_id: uuid.UUID | None,
    provider: str,
) -> ModelCredential | None:
    statement = (
        select(ModelCredential)
        .where(
            ModelCredential.owner_type == owner_type,
            ModelCredential.provider == provider,
            ModelCredential.is_active.is_(True),
        )
        .order_by(ModelCredential.updated_at.desc(), ModelCredential.created_at.desc())
    )
    owner_statement = statement.where(ModelCredential.owner_id.is_(None))
    if owner_id is not None:
        owner_statement = statement.where(ModelCredential.owner_id == owner_id)
    return await db.scalar(owner_statement)


async def ensure_credential_is_deletable(
    db: AsyncSession,
    credential_id: uuid.UUID,
) -> None:
    usage_id = await db.scalar(
        select(TokenUsage.id).where(TokenUsage.credential_id == credential_id).limit(1)
    )
    if usage_id is not None:
        raise BusinessRuleError(CREDENTIAL_DELETE_IN_USE_MESSAGE)


def scope_statement(scope: CredentialScope) -> Select[tuple[ModelCredential]]:
    statement = select(ModelCredential).where(ModelCredential.owner_type == scope.owner_type)
    if scope.owner_id is None:
        return statement.where(ModelCredential.owner_id.is_(None))
    return statement.where(ModelCredential.owner_id == scope.owner_id)
