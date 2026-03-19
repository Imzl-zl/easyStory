from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.modules.content.service import StoryAssetDTO, StoryAssetSaveDTO, StoryAssetService
from app.shared.db import get_db_session

router = APIRouter(prefix="/api/v1/projects/{project_id}", tags=["preparation"])


@router.put("/outline", response_model=StoryAssetDTO)
def save_outline_draft(
    project_id: uuid.UUID,
    payload: StoryAssetSaveDTO,
    db: Session = Depends(get_db_session),
) -> StoryAssetDTO:
    return StoryAssetService().save_asset_draft(db, project_id, "outline", payload)


@router.post("/outline/approve", response_model=StoryAssetDTO)
def approve_outline(
    project_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> StoryAssetDTO:
    return StoryAssetService().approve_asset(db, project_id, "outline")


@router.put("/opening-plan", response_model=StoryAssetDTO)
def save_opening_plan_draft(
    project_id: uuid.UUID,
    payload: StoryAssetSaveDTO,
    db: Session = Depends(get_db_session),
) -> StoryAssetDTO:
    return StoryAssetService().save_asset_draft(db, project_id, "opening_plan", payload)


@router.post("/opening-plan/approve", response_model=StoryAssetDTO)
def approve_opening_plan(
    project_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> StoryAssetDTO:
    return StoryAssetService().approve_asset(db, project_id, "opening_plan")
