from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.modules.credential.service import (
    CredentialCreateDTO,
    CredentialService,
    CredentialUpdateDTO,
    CredentialVerifyResultDTO,
    CredentialViewDTO,
    create_credential_service,
)
from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.shared.db import get_db_session

router = APIRouter(prefix="/api/v1/credentials", tags=["credentials"])


def get_credential_service() -> CredentialService:
    return create_credential_service()


@router.get("", response_model=list[CredentialViewDTO])
def list_credentials(
    owner_type: Literal["user", "project"] = Query(default="user"),
    project_id: uuid.UUID | None = Query(default=None),
    credential_service: CredentialService = Depends(get_credential_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[CredentialViewDTO]:
    return credential_service.list_credentials(
        db,
        actor_user_id=current_user.id,
        owner_type=owner_type,
        project_id=project_id,
    )


@router.post("", response_model=CredentialViewDTO)
def create_credential(
    payload: CredentialCreateDTO,
    credential_service: CredentialService = Depends(get_credential_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> CredentialViewDTO:
    return credential_service.create_credential(
        db,
        payload,
        actor_user_id=current_user.id,
    )


@router.put("/{credential_id}", response_model=CredentialViewDTO)
def update_credential(
    credential_id: uuid.UUID,
    payload: CredentialUpdateDTO,
    credential_service: CredentialService = Depends(get_credential_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> CredentialViewDTO:
    return credential_service.update_credential(
        db,
        credential_id,
        payload,
        actor_user_id=current_user.id,
    )


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(
    credential_id: uuid.UUID,
    credential_service: CredentialService = Depends(get_credential_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> Response:
    credential_service.delete_credential(
        db,
        credential_id,
        actor_user_id=current_user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{credential_id}/verify", response_model=CredentialVerifyResultDTO)
def verify_credential(
    credential_id: uuid.UUID,
    credential_service: CredentialService = Depends(get_credential_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> CredentialVerifyResultDTO:
    return credential_service.verify_credential(
        db,
        credential_id,
        actor_user_id=current_user.id,
    )


@router.post("/{credential_id}/enable", response_model=CredentialViewDTO)
def enable_credential(
    credential_id: uuid.UUID,
    credential_service: CredentialService = Depends(get_credential_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> CredentialViewDTO:
    return credential_service.enable_credential(
        db,
        credential_id,
        actor_user_id=current_user.id,
    )


@router.post("/{credential_id}/disable", response_model=CredentialViewDTO)
def disable_credential(
    credential_id: uuid.UUID,
    credential_service: CredentialService = Depends(get_credential_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> CredentialViewDTO:
    return credential_service.disable_credential(
        db,
        credential_id,
        actor_user_id=current_user.id,
    )
