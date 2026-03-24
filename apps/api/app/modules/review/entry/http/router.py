from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.review.service import (
    ReviewQueryService,
    ReviewStatus,
    WorkflowReviewActionDTO,
    WorkflowReviewSummaryDTO,
    create_review_query_service,
)
from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.shared.db import get_async_db_session

router = APIRouter(tags=["review"])


async def get_review_query_service() -> ReviewQueryService:
    return create_review_query_service()


@router.get(
    "/api/v1/workflows/{workflow_id}/reviews/summary",
    response_model=WorkflowReviewSummaryDTO,
)
async def get_workflow_review_summary(
    workflow_id: uuid.UUID,
    node_execution_id: uuid.UUID | None = Query(default=None),
    review_type: str | None = Query(default=None, min_length=1),
    status: ReviewStatus | None = Query(default=None),
    review_query_service: ReviewQueryService = Depends(get_review_query_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> WorkflowReviewSummaryDTO:
    return await review_query_service.get_workflow_summary(
        db,
        workflow_id,
        owner_id=current_user.id,
        node_execution_id=node_execution_id,
        review_type=review_type,
        status=status,
    )


@router.get(
    "/api/v1/workflows/{workflow_id}/reviews/actions",
    response_model=list[WorkflowReviewActionDTO],
)
async def list_workflow_review_actions(
    workflow_id: uuid.UUID,
    node_execution_id: uuid.UUID | None = Query(default=None),
    review_type: str | None = Query(default=None, min_length=1),
    status: ReviewStatus | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    review_query_service: ReviewQueryService = Depends(get_review_query_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> list[WorkflowReviewActionDTO]:
    return await review_query_service.list_workflow_review_actions(
        db,
        workflow_id,
        owner_id=current_user.id,
        node_execution_id=node_execution_id,
        review_type=review_type,
        status=status,
        limit=limit,
    )
