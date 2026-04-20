from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.context.service.context_preview_service import ContextPreviewService
from app.modules.context.service.dto import (
    ContextPreviewDTO,
    ContextPreviewRequestDTO,
    StoryFactConflictStatus,
    StoryFactCreateDTO,
    StoryFactDTO,
    StoryFactMutationResultDTO,
    StoryFactSupersedeDTO,
    StoryFactType,
)
from app.modules.context.service.factory import create_context_preview_service
from app.modules.context.service.story_bible_factory import create_story_bible_service
from app.modules.context.service.story_bible_service import StoryBibleService
from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.shared.db import get_async_db_session

router = APIRouter(tags=["context"])


def get_context_preview_service() -> ContextPreviewService:
    return create_context_preview_service()


def get_story_bible_service() -> StoryBibleService:
    return create_story_bible_service()


@router.post(
    "/api/v1/workflows/{workflow_id}/context-preview",
    response_model=ContextPreviewDTO,
)
async def preview_workflow_context(
    workflow_id: uuid.UUID,
    payload: ContextPreviewRequestDTO,
    context_preview_service: ContextPreviewService = Depends(get_context_preview_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ContextPreviewDTO:
    return await context_preview_service.preview_workflow_context(
        db,
        workflow_id,
        payload,
        owner_id=current_user.id,
    )


@router.get(
    "/api/v1/projects/{project_id}/story-bible",
    response_model=list[StoryFactDTO],
)
async def list_story_bible_facts(
    project_id: uuid.UUID,
    fact_type: StoryFactType | None = Query(default=None),
    conflict_status: StoryFactConflictStatus | None = Query(default=None),
    active_only: bool = Query(default=True),
    chapter_number: int | None = Query(default=None, ge=1),
    source_content_version_id: uuid.UUID | None = Query(default=None),
    visible_at_chapter: int | None = Query(default=None, ge=1),
    limit: int = Query(default=200, ge=1, le=200),
    story_bible_service: StoryBibleService = Depends(get_story_bible_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> list[StoryFactDTO]:
    return await story_bible_service.list_facts(
        db,
        project_id,
        owner_id=current_user.id,
        fact_type=fact_type,
        conflict_status=conflict_status,
        active_only=active_only,
        chapter_number=chapter_number,
        source_content_version_id=source_content_version_id,
        visible_at_chapter=visible_at_chapter,
        limit=limit,
    )


@router.get(
    "/api/v1/projects/{project_id}/story-bible/{fact_id}",
    response_model=StoryFactDTO,
)
async def get_story_bible_fact(
    project_id: uuid.UUID,
    fact_id: uuid.UUID,
    story_bible_service: StoryBibleService = Depends(get_story_bible_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> StoryFactDTO:
    return await story_bible_service.get_fact(
        db,
        project_id,
        fact_id,
        owner_id=current_user.id,
    )


@router.post(
    "/api/v1/projects/{project_id}/story-bible",
    response_model=StoryFactMutationResultDTO,
)
async def create_story_bible_fact(
    project_id: uuid.UUID,
    payload: StoryFactCreateDTO,
    story_bible_service: StoryBibleService = Depends(get_story_bible_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> StoryFactMutationResultDTO:
    return await story_bible_service.create_fact(
        db,
        project_id,
        payload,
        owner_id=current_user.id,
    )


@router.post(
    "/api/v1/projects/{project_id}/story-bible/{fact_id}/confirm-conflict",
    response_model=StoryFactMutationResultDTO,
)
async def confirm_story_bible_conflict(
    project_id: uuid.UUID,
    fact_id: uuid.UUID,
    story_bible_service: StoryBibleService = Depends(get_story_bible_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> StoryFactMutationResultDTO:
    return await story_bible_service.confirm_conflict(
        db,
        project_id,
        fact_id,
        owner_id=current_user.id,
    )


@router.post(
    "/api/v1/projects/{project_id}/story-bible/{fact_id}/supersede",
    response_model=StoryFactMutationResultDTO,
)
async def supersede_story_bible_fact(
    project_id: uuid.UUID,
    fact_id: uuid.UUID,
    payload: StoryFactSupersedeDTO,
    story_bible_service: StoryBibleService = Depends(get_story_bible_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> StoryFactMutationResultDTO:
    return await story_bible_service.supersede_fact(
        db,
        project_id,
        fact_id,
        payload,
        owner_id=current_user.id,
    )
