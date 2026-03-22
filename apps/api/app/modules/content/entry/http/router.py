from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content.service import (
    AssetType,
    ChapterContentService,
    ChapterDetailDTO,
    ChapterSaveDTO,
    ChapterSummaryDTO,
    ChapterVersionDTO,
    StoryAssetService,
    StoryAssetDTO,
    StoryAssetSaveDTO,
    StoryAssetVersionDTO,
    create_chapter_content_service,
    create_story_asset_service,
)
from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.shared.db import get_async_db_session

router = APIRouter(prefix="/api/v1/projects/{project_id}", tags=["content"])


def get_story_asset_service() -> StoryAssetService:
    return create_story_asset_service()


def get_chapter_content_service() -> ChapterContentService:
    return create_chapter_content_service()


@router.put("/outline", response_model=StoryAssetDTO)
async def save_outline_draft(
    project_id: uuid.UUID,
    payload: StoryAssetSaveDTO,
    story_asset_service: StoryAssetService = Depends(get_story_asset_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> StoryAssetDTO:
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


@router.post("/outline/approve", response_model=StoryAssetDTO)
async def approve_outline(
    project_id: uuid.UUID,
    story_asset_service: StoryAssetService = Depends(get_story_asset_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> StoryAssetDTO:
    return await story_asset_service.approve_asset(
        db,
        project_id,
        "outline",
        owner_id=current_user.id,
    )


@router.put("/opening-plan", response_model=StoryAssetDTO)
async def save_opening_plan_draft(
    project_id: uuid.UUID,
    payload: StoryAssetSaveDTO,
    story_asset_service: StoryAssetService = Depends(get_story_asset_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> StoryAssetDTO:
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


@router.post("/opening-plan/approve", response_model=StoryAssetDTO)
async def approve_opening_plan(
    project_id: uuid.UUID,
    story_asset_service: StoryAssetService = Depends(get_story_asset_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> StoryAssetDTO:
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


@router.get("/chapters", response_model=list[ChapterSummaryDTO])
async def list_chapters(
    project_id: uuid.UUID,
    chapter_content_service: ChapterContentService = Depends(get_chapter_content_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> list[ChapterSummaryDTO]:
    return await chapter_content_service.list_chapters(
        db,
        project_id,
        owner_id=current_user.id,
    )


@router.get("/chapters/{chapter_number}", response_model=ChapterDetailDTO)
async def get_chapter(
    project_id: uuid.UUID,
    chapter_number: int,
    chapter_content_service: ChapterContentService = Depends(get_chapter_content_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ChapterDetailDTO:
    return await chapter_content_service.get_chapter(
        db,
        project_id,
        chapter_number,
        owner_id=current_user.id,
    )


@router.put("/chapters/{chapter_number}", response_model=ChapterDetailDTO)
async def save_chapter_draft(
    project_id: uuid.UUID,
    chapter_number: int,
    payload: ChapterSaveDTO,
    chapter_content_service: ChapterContentService = Depends(get_chapter_content_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ChapterDetailDTO:
    return await chapter_content_service.save_chapter_draft(
        db,
        project_id,
        chapter_number,
        payload,
        owner_id=current_user.id,
    )


@router.post("/chapters/{chapter_number}/approve", response_model=ChapterDetailDTO)
async def approve_chapter(
    project_id: uuid.UUID,
    chapter_number: int,
    chapter_content_service: ChapterContentService = Depends(get_chapter_content_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ChapterDetailDTO:
    return await chapter_content_service.approve_chapter(
        db,
        project_id,
        chapter_number,
        owner_id=current_user.id,
    )


@router.get("/chapters/{chapter_number}/versions", response_model=list[ChapterVersionDTO])
async def list_chapter_versions(
    project_id: uuid.UUID,
    chapter_number: int,
    chapter_content_service: ChapterContentService = Depends(get_chapter_content_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> list[ChapterVersionDTO]:
    return await chapter_content_service.list_versions(
        db,
        project_id,
        chapter_number,
        owner_id=current_user.id,
    )


@router.post(
    "/chapters/{chapter_number}/versions/{version_number}/rollback",
    response_model=ChapterDetailDTO,
)
async def rollback_chapter_version(
    project_id: uuid.UUID,
    chapter_number: int,
    version_number: int,
    chapter_content_service: ChapterContentService = Depends(get_chapter_content_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ChapterDetailDTO:
    return await chapter_content_service.rollback_version(
        db,
        project_id,
        chapter_number,
        version_number,
        owner_id=current_user.id,
    )


@router.post(
    "/chapters/{chapter_number}/versions/{version_number}/best",
    response_model=ChapterVersionDTO,
)
async def mark_best_version(
    project_id: uuid.UUID,
    chapter_number: int,
    version_number: int,
    chapter_content_service: ChapterContentService = Depends(get_chapter_content_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ChapterVersionDTO:
    return await chapter_content_service.mark_best_version(
        db,
        project_id,
        chapter_number,
        version_number,
        owner_id=current_user.id,
    )


@router.delete(
    "/chapters/{chapter_number}/versions/{version_number}/best",
    response_model=ChapterVersionDTO,
)
async def clear_best_version(
    project_id: uuid.UUID,
    chapter_number: int,
    version_number: int,
    chapter_content_service: ChapterContentService = Depends(get_chapter_content_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ChapterVersionDTO:
    return await chapter_content_service.clear_best_version(
        db,
        project_id,
        chapter_number,
        version_number,
        owner_id=current_user.id,
    )
