from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.credential.models import ModelCredential
from app.modules.project.service import ProjectService

from .credential_query_support import (
    OWNER_TYPE_PROJECT,
    OWNER_TYPE_SYSTEM,
    OWNER_TYPE_USER,
    find_active_credential,
    load_project_if_present,
)
from .credential_service_support import (
    ResolvedCredentialModel,
    normalize_provider,
    resolve_model_name,
)


async def resolve_active_credential_record(
    db: AsyncSession,
    *,
    provider: str,
    user_id: uuid.UUID,
    project_id: uuid.UUID | None,
    project_service: ProjectService,
) -> ModelCredential:
    normalized_provider = normalize_provider(provider)
    project = await load_project_if_present(
        db,
        project_id,
        owner_id=user_id,
        project_service=project_service,
    )
    if project is not None:
        project_credential = await find_active_credential(
            db,
            owner_type=OWNER_TYPE_PROJECT,
            owner_id=project.id,
            provider=normalized_provider,
        )
        if project_credential is not None:
            return project_credential
    user_credential = await find_active_credential(
        db,
        owner_type=OWNER_TYPE_USER,
        owner_id=user_id,
        provider=normalized_provider,
    )
    if user_credential is not None:
        return user_credential
    if project is not None and project.allow_system_credential_pool:
        system_credential = await find_active_credential(
            db,
            owner_type=OWNER_TYPE_SYSTEM,
            owner_id=None,
            provider=normalized_provider,
        )
        if system_credential is not None:
            return system_credential
    raise LookupError(normalized_provider)


async def resolve_active_credential_model_record(
    db: AsyncSession,
    *,
    provider: str,
    requested_model_name: str | None,
    user_id: uuid.UUID,
    project_id: uuid.UUID | None,
    project_service: ProjectService,
) -> ResolvedCredentialModel:
    credential = await resolve_active_credential_record(
        db,
        provider=provider,
        user_id=user_id,
        project_id=project_id,
        project_service=project_service,
    )
    return ResolvedCredentialModel(
        credential=credential,
        model_name=resolve_model_name(
            requested_model_name=requested_model_name,
            default_model=credential.default_model,
            provider=credential.provider,
        ),
    )
