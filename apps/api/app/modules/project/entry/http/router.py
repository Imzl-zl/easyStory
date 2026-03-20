from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.modules.project.service import (
    ProjectService,
    ProjectSettingSnapshotDTO,
    ProjectSettingUpdateDTO,
    SettingCompletenessResultDTO,
    create_project_service,
)
from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.shared.db import get_db_session

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


def get_project_service() -> ProjectService:
    return create_project_service()


@router.put("/{project_id}/setting", response_model=ProjectSettingSnapshotDTO)
def update_project_setting(
    project_id: uuid.UUID,
    payload: ProjectSettingUpdateDTO,
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ProjectSettingSnapshotDTO:
    return project_service.update_project_setting(
        db,
        project_id,
        payload,
        owner_id=current_user.id,
    )


@router.post(
    "/{project_id}/setting/complete-check",
    response_model=SettingCompletenessResultDTO,
)
def check_project_setting_completeness(
    project_id: uuid.UUID,
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> SettingCompletenessResultDTO:
    return project_service.check_setting_completeness(
        db,
        project_id,
        owner_id=current_user.id,
    )
