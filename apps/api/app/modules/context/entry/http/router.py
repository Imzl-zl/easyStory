from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.modules.context.service import (
    ContextPreviewDTO,
    ContextPreviewRequestDTO,
    ContextPreviewService,
    create_context_preview_service,
)
from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.shared.db import get_db_session

router = APIRouter(tags=["context"])


def get_context_preview_service() -> ContextPreviewService:
    return create_context_preview_service()


@router.post(
    "/api/v1/workflows/{workflow_id}/context-preview",
    response_model=ContextPreviewDTO,
)
def preview_workflow_context(
    workflow_id: uuid.UUID,
    payload: ContextPreviewRequestDTO,
    context_preview_service: ContextPreviewService = Depends(get_context_preview_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ContextPreviewDTO:
    return context_preview_service.preview_workflow_context(
        db,
        workflow_id,
        payload,
        owner_id=current_user.id,
    )
