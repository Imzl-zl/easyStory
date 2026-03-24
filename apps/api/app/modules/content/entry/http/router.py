from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content.service import (
    ChapterContentService,
    ChapterDetailDTO,
    ChapterSaveDTO,
    ChapterSummaryDTO,
    ChapterVersionDTO,
    create_chapter_content_service,
)
from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.shared.db import get_async_db_session

from .story_asset_router import router as story_asset_router

router = APIRouter(prefix="/api/v1/projects/{project_id}", tags=["content"])
router.include_router(story_asset_router)


def get_chapter_content_service() -> ChapterContentService:
    return create_chapter_content_service()


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
