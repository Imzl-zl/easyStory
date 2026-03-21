from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.modules.project.service import (
    ProjectCreateDTO,
    ProjectDetailDTO,
    ProjectManagementService,
    ProjectService,
    ProjectSettingSnapshotDTO,
    ProjectSettingUpdateDTO,
    ProjectSummaryDTO,
    ProjectUpdateDTO,
    SettingCompletenessResultDTO,
    create_project_management_service,
    create_project_service,
)
from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.shared.db import get_db_session

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


def get_project_service() -> ProjectService:
    return create_project_service()


def get_project_management_service() -> ProjectManagementService:
    return create_project_management_service()


@router.post("", response_model=ProjectDetailDTO)
def create_project(
    payload: ProjectCreateDTO,
    project_management_service: ProjectManagementService = Depends(
        get_project_management_service
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ProjectDetailDTO:
    return project_management_service.create_project(
        db,
        payload,
        owner_id=current_user.id,
    )


@router.get("", response_model=list[ProjectSummaryDTO])
def list_projects(
    deleted_only: bool = Query(default=False),
    project_management_service: ProjectManagementService = Depends(
        get_project_management_service
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[ProjectSummaryDTO]:
    return project_management_service.list_projects(
        db,
        owner_id=current_user.id,
        deleted_only=deleted_only,
    )


@router.get("/{project_id}", response_model=ProjectDetailDTO)
def get_project(
    project_id: uuid.UUID,
    project_management_service: ProjectManagementService = Depends(
        get_project_management_service
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ProjectDetailDTO:
    return project_management_service.get_project(
        db,
        project_id,
        owner_id=current_user.id,
    )


@router.put("/{project_id}", response_model=ProjectDetailDTO)
def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdateDTO,
    project_management_service: ProjectManagementService = Depends(
        get_project_management_service
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ProjectDetailDTO:
    return project_management_service.update_project(
        db,
        project_id,
        payload,
        owner_id=current_user.id,
    )


@router.delete("/{project_id}", response_model=ProjectDetailDTO)
def soft_delete_project(
    project_id: uuid.UUID,
    project_management_service: ProjectManagementService = Depends(
        get_project_management_service
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ProjectDetailDTO:
    return project_management_service.soft_delete_project(
        db,
        project_id,
        owner_id=current_user.id,
    )


@router.post("/{project_id}/restore", response_model=ProjectDetailDTO)
def restore_project(
    project_id: uuid.UUID,
    project_management_service: ProjectManagementService = Depends(
        get_project_management_service
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ProjectDetailDTO:
    return project_management_service.restore_project(
        db,
        project_id,
        owner_id=current_user.id,
    )


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
