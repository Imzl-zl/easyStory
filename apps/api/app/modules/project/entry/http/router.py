from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.modules.project.service import (
    ProjectService,
    ProjectSettingSnapshotDTO,
    ProjectSettingUpdateDTO,
    SettingCompletenessResultDTO,
)
from app.shared.db import get_db_session

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.put("/{project_id}/setting", response_model=ProjectSettingSnapshotDTO)
def update_project_setting(
    project_id: uuid.UUID,
    payload: ProjectSettingUpdateDTO,
    db: Session = Depends(get_db_session),
) -> ProjectSettingSnapshotDTO:
    service = ProjectService()
    return service.update_project_setting(db, project_id, payload)


@router.post(
    "/{project_id}/setting/complete-check",
    response_model=SettingCompletenessResultDTO,
)
def check_project_setting_completeness(
    project_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> SettingCompletenessResultDTO:
    service = ProjectService()
    return service.check_setting_completeness(db, project_id)
