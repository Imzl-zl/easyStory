from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assistant.service import (
    AssistantService,
    AssistantTurnRequestDTO,
    AssistantTurnResponseDTO,
    create_assistant_service,
)
from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.shared.db import get_async_db_session

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])


def get_assistant_service() -> AssistantService:
    return create_assistant_service()


@router.post("/turn", response_model=AssistantTurnResponseDTO)
async def run_assistant_turn(
    payload: AssistantTurnRequestDTO,
    assistant_service: AssistantService = Depends(get_assistant_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantTurnResponseDTO:
    return await assistant_service.turn(
        db,
        payload,
        owner_id=current_user.id,
    )
