from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content.service import (
    AssetType,
    StoryAssetDTO,
    StoryAssetGenerateDTO,
    StoryAssetGenerationService,
    StoryAssetMutationDTO,
    StoryAssetSaveDTO,
    StoryAssetService,
    StoryAssetVersionDTO,
    create_story_asset_generation_service,
    create_story_asset_service,
)
from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.shared.db import get_async_db_session

router = APIRouter()


def get_story_asset_service() -> StoryAssetService:
    return create_story_asset_service()


def get_story_asset_generation_service() -> StoryAssetGenerationService:
    return create_story_asset_generation_service()


@router.put("/outline", response_model=StoryAssetMutationDTO)
async def save_outline_draft(
    project_id: uuid.UUID,
    payload: StoryAssetSaveDTO,
    story_asset_service: StoryAssetService = Depends(get_story_asset_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> StoryAssetMutationDTO:
    return await story_asset_service.save_asset_draft(
        db,
        project_id,
        "outline",
        payload,
        owner_id=current_user.id,
    )


@router.get("/outline", response_model=StoryAssetDTO)
async def get_outline(
    project_id: uuid.UUID,
    story_asset_service: StoryAssetService = Depends(get_story_asset_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> StoryAssetDTO:
    return await story_asset_service.get_asset(
        db,
        project_id,
        "outline",
        owner_id=current_user.id,
    )


@router.post("/outline/generate", response_model=StoryAssetMutationDTO)
async def generate_outline(
    project_id: uuid.UUID,
    payload: StoryAssetGenerateDTO | None = None,
    story_asset_generation_service: StoryAssetGenerationService = Depends(
        get_story_asset_generation_service
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> StoryAssetMutationDTO:
    return await story_asset_generation_service.generate_asset(
        db,
        project_id,
        "outline",
        payload or StoryAssetGenerateDTO(),
        owner_id=current_user.id,
    )


@router.post("/outline/approve", response_model=StoryAssetMutationDTO)
async def approve_outline(
    project_id: uuid.UUID,
    story_asset_service: StoryAssetService = Depends(get_story_asset_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> StoryAssetMutationDTO:
    return await story_asset_service.approve_asset(
        db,
        project_id,
        "outline",
        owner_id=current_user.id,
    )


@router.put("/opening-plan", response_model=StoryAssetMutationDTO)
async def save_opening_plan_draft(
    project_id: uuid.UUID,
    payload: StoryAssetSaveDTO,
    story_asset_service: StoryAssetService = Depends(get_story_asset_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> StoryAssetMutationDTO:
    return await story_asset_service.save_asset_draft(
        db,
        project_id,
        "opening_plan",
        payload,
        owner_id=current_user.id,
    )


@router.get("/opening-plan", response_model=StoryAssetDTO)
async def get_opening_plan(
    project_id: uuid.UUID,
    story_asset_service: StoryAssetService = Depends(get_story_asset_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> StoryAssetDTO:
    return await story_asset_service.get_asset(
        db,
        project_id,
        "opening_plan",
        owner_id=current_user.id,
    )


@router.post("/opening-plan/generate", response_model=StoryAssetMutationDTO)
async def generate_opening_plan(
    project_id: uuid.UUID,
    payload: StoryAssetGenerateDTO | None = None,
    story_asset_generation_service: StoryAssetGenerationService = Depends(
        get_story_asset_generation_service
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> StoryAssetMutationDTO:
    return await story_asset_generation_service.generate_asset(
        db,
        project_id,
        "opening_plan",
        payload or StoryAssetGenerateDTO(),
        owner_id=current_user.id,
    )


@router.post("/opening-plan/approve", response_model=StoryAssetMutationDTO)
async def approve_opening_plan(
    project_id: uuid.UUID,
    story_asset_service: StoryAssetService = Depends(get_story_asset_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> StoryAssetMutationDTO:
    return await story_asset_service.approve_asset(
        db,
        project_id,
        "opening_plan",
        owner_id=current_user.id,
    )


@router.get("/story-assets/{asset_type}/versions", response_model=list[StoryAssetVersionDTO])
async def list_story_asset_versions(
    project_id: uuid.UUID,
    asset_type: AssetType,
    story_asset_service: StoryAssetService = Depends(get_story_asset_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> list[StoryAssetVersionDTO]:
    return await story_asset_service.list_versions(
        db,
        project_id,
        asset_type,
        owner_id=current_user.id,
    )
