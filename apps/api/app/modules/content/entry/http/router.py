from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.modules.content.service import (
    StoryAssetDTO,
    StoryAssetSaveDTO,
    StoryAssetService,
    create_story_asset_service,
)
from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.shared.db import get_db_session

router = APIRouter(prefix="/api/v1/projects/{project_id}", tags=["preparation"])


def get_story_asset_service() -> StoryAssetService:
    return create_story_asset_service()


@router.put("/outline", response_model=StoryAssetDTO)
def save_outline_draft(
    project_id: uuid.UUID,
    payload: StoryAssetSaveDTO,
    story_asset_service: StoryAssetService = Depends(get_story_asset_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> StoryAssetDTO:
    return story_asset_service.save_asset_draft(
        db,
        project_id,
        "outline",
        payload,
        owner_id=current_user.id,
    )


@router.post("/outline/approve", response_model=StoryAssetDTO)
def approve_outline(
    project_id: uuid.UUID,
    story_asset_service: StoryAssetService = Depends(get_story_asset_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> StoryAssetDTO:
    return story_asset_service.approve_asset(
        db,
        project_id,
        "outline",
        owner_id=current_user.id,
    )


@router.put("/opening-plan", response_model=StoryAssetDTO)
def save_opening_plan_draft(
    project_id: uuid.UUID,
    payload: StoryAssetSaveDTO,
    story_asset_service: StoryAssetService = Depends(get_story_asset_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> StoryAssetDTO:
    return story_asset_service.save_asset_draft(
        db,
        project_id,
        "opening_plan",
        payload,
        owner_id=current_user.id,
    )


@router.post("/opening-plan/approve", response_model=StoryAssetDTO)
def approve_opening_plan(
    project_id: uuid.UUID,
    story_asset_service: StoryAssetService = Depends(get_story_asset_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> StoryAssetDTO:
    return story_asset_service.approve_asset(
        db,
        project_id,
        "opening_plan",
        owner_id=current_user.id,
    )
