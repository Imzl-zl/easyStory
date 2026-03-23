from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.project.service import (
    ProjectPreparationStatusDTO,
    ProjectCreateDTO,
    ProjectDeletionService,
    ProjectDetailDTO,
    ProjectIncubatorConversationDraftDTO,
    ProjectIncubatorConversationDraftRequestDTO,
    ProjectIncubatorCreateRequestDTO,
    ProjectIncubatorCreateResultDTO,
    ProjectIncubatorDraftDTO,
    ProjectIncubatorDraftRequestDTO,
    ProjectIncubatorService,
    ProjectManagementService,
    ProjectService,
    ProjectSettingSnapshotDTO,
    ProjectSettingUpdateDTO,
    ProjectSummaryDTO,
    ProjectUpdateDTO,
    SettingCompletenessResultDTO,
    create_project_deletion_service,
    create_project_incubator_service,
    create_project_management_service,
    create_project_service,
)
from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.shared.db import get_async_db_session

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


def get_project_service() -> ProjectService:
    return create_project_service()


def get_project_management_service() -> ProjectManagementService:
    return create_project_management_service()


def get_project_incubator_service() -> ProjectIncubatorService:
    return create_project_incubator_service()


def get_project_deletion_service() -> ProjectDeletionService:
    return create_project_deletion_service()


@router.post("", response_model=ProjectDetailDTO)
async def create_project(
    payload: ProjectCreateDTO,
    project_management_service: ProjectManagementService = Depends(
        get_project_management_service
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ProjectDetailDTO:
    return await project_management_service.create_project(
        db,
        payload,
        owner_id=current_user.id,
    )


@router.get("", response_model=list[ProjectSummaryDTO])
async def list_projects(
    deleted_only: bool = Query(default=False),
    project_management_service: ProjectManagementService = Depends(
        get_project_management_service
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> list[ProjectSummaryDTO]:
    return await project_management_service.list_projects(
        db,
        owner_id=current_user.id,
        deleted_only=deleted_only,
    )


@router.post("/incubator/draft-setting", response_model=ProjectIncubatorDraftDTO)
async def build_incubator_project_setting_draft(
    payload: ProjectIncubatorDraftRequestDTO,
    project_incubator_service: ProjectIncubatorService = Depends(
        get_project_incubator_service
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ProjectIncubatorDraftDTO:
    del current_user
    return await project_incubator_service.build_draft(db, payload)


@router.post(
    "/incubator/conversation/draft-setting",
    response_model=ProjectIncubatorConversationDraftDTO,
)
async def build_incubator_project_setting_draft_from_conversation(
    payload: ProjectIncubatorConversationDraftRequestDTO,
    project_incubator_service: ProjectIncubatorService = Depends(
        get_project_incubator_service
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ProjectIncubatorConversationDraftDTO:
    return await project_incubator_service.build_conversation_draft(
        db,
        payload,
        owner_id=current_user.id,
    )


@router.post(
    "/incubator/create-project",
    response_model=ProjectIncubatorCreateResultDTO,
)
async def create_project_from_incubator(
    payload: ProjectIncubatorCreateRequestDTO,
    project_incubator_service: ProjectIncubatorService = Depends(
        get_project_incubator_service
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ProjectIncubatorCreateResultDTO:
    return await project_incubator_service.create_project(
        db,
        payload,
        owner_id=current_user.id,
    )


@router.get("/{project_id}", response_model=ProjectDetailDTO)
async def get_project(
    project_id: uuid.UUID,
    project_management_service: ProjectManagementService = Depends(
        get_project_management_service
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ProjectDetailDTO:
    return await project_management_service.get_project(
        db,
        project_id,
        owner_id=current_user.id,
    )


@router.put("/{project_id}", response_model=ProjectDetailDTO)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdateDTO,
    project_management_service: ProjectManagementService = Depends(
        get_project_management_service
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ProjectDetailDTO:
    return await project_management_service.update_project(
        db,
        project_id,
        payload,
        owner_id=current_user.id,
    )


@router.delete("/{project_id}", response_model=ProjectDetailDTO)
async def soft_delete_project(
    project_id: uuid.UUID,
    project_deletion_service: ProjectDeletionService = Depends(
        get_project_deletion_service
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ProjectDetailDTO:
    return await project_deletion_service.soft_delete_project(
        db,
        project_id,
        owner_id=current_user.id,
    )


@router.post("/{project_id}/restore", response_model=ProjectDetailDTO)
async def restore_project(
    project_id: uuid.UUID,
    project_deletion_service: ProjectDeletionService = Depends(
        get_project_deletion_service
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ProjectDetailDTO:
    return await project_deletion_service.restore_project(
        db,
        project_id,
        owner_id=current_user.id,
    )


@router.delete("/{project_id}/physical", status_code=status.HTTP_204_NO_CONTENT)
async def physical_delete_project(
    project_id: uuid.UUID,
    project_deletion_service: ProjectDeletionService = Depends(
        get_project_deletion_service
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> Response:
    await project_deletion_service.physical_delete_project(
        db,
        project_id,
        owner_id=current_user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{project_id}/setting", response_model=ProjectSettingSnapshotDTO)
async def update_project_setting(
    project_id: uuid.UUID,
    payload: ProjectSettingUpdateDTO,
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ProjectSettingSnapshotDTO:
    return await project_service.update_project_setting(
        db,
        project_id,
        payload,
        owner_id=current_user.id,
    )


@router.post(
    "/{project_id}/setting/complete-check",
    response_model=SettingCompletenessResultDTO,
)
async def check_project_setting_completeness(
    project_id: uuid.UUID,
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> SettingCompletenessResultDTO:
    return await project_service.check_setting_completeness(
        db,
        project_id,
        owner_id=current_user.id,
    )


@router.get(
    "/{project_id}/preparation/status",
    response_model=ProjectPreparationStatusDTO,
)
async def get_project_preparation_status(
    project_id: uuid.UUID,
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ProjectPreparationStatusDTO:
    return await project_service.get_preparation_status(
        db,
        project_id,
        owner_id=current_user.id,
    )
