from __future__ import annotations

from collections.abc import AsyncIterator
import json
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assistant.service import (
    AssistantPreferencesDTO,
    AssistantPreferencesService,
    AssistantPreferencesUpdateDTO,
    AssistantRuleProfileDTO,
    AssistantRuleProfileUpdateDTO,
    AssistantRuleService,
    AssistantService,
    AssistantTurnRequestDTO,
    AssistantTurnResponseDTO,
    create_assistant_preferences_service,
    create_assistant_rule_service,
    create_assistant_service,
)
from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.shared.db import get_async_db_session
from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.provider_interop_stream_support import StreamInterruptedError

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])
ASSISTANT_TURN_RESPONSE_SCHEMA = AssistantTurnResponseDTO.model_json_schema()


def get_assistant_service() -> AssistantService:
    return create_assistant_service()


def get_assistant_rule_service() -> AssistantRuleService:
    return create_assistant_rule_service()


def get_assistant_preferences_service() -> AssistantPreferencesService:
    return create_assistant_preferences_service()


@router.post(
    "/turn",
    response_model=None,
    responses={
        200: {
            "content": {
                "application/json": {"schema": ASSISTANT_TURN_RESPONSE_SCHEMA},
                "text/event-stream": {"schema": {"type": "string"}},
            }
        }
    },
)
async def run_assistant_turn(
    request: Request,
    payload: AssistantTurnRequestDTO,
    assistant_service: AssistantService = Depends(get_assistant_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantTurnResponseDTO | StreamingResponse:
    if payload.stream:
        return StreamingResponse(
            _iter_assistant_turn_events(
                assistant_service,
                request=request,
                db=db,
                payload=payload,
                owner_id=current_user.id,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    return await assistant_service.turn(
        db,
        payload,
        owner_id=current_user.id,
    )


async def _iter_assistant_turn_events(
    assistant_service: AssistantService,
    *,
    request: Request,
    db: AsyncSession,
    payload: AssistantTurnRequestDTO,
    owner_id: uuid.UUID,
) -> AsyncIterator[str]:
    try:
        async for event in assistant_service.stream_turn(
            db,
            payload,
            owner_id=owner_id,
            should_stop=request.is_disconnected,
        ):
            yield _format_sse_event(event.event, event.data)
    except StreamInterruptedError:
        return
    except Exception as exc:
        yield _format_sse_event("error", {"message": _resolve_assistant_stream_error_message(exc)})


def _format_sse_event(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _resolve_assistant_stream_error_message(error: Exception) -> str:
    detail = str(error).strip()
    if isinstance(error, ConfigurationError):
        if detail:
            return f"这次回复失败了，请检查模型连接后重试。上游提示：{detail}"
        return "这次回复失败了，请检查模型连接后重试。"
    if detail:
        return f"这次回复中断了，请重试。详细信息：{detail}"
    return "这次回复中断了，请重试。"


@router.get("/preferences", response_model=AssistantPreferencesDTO)
async def get_my_assistant_preferences(
    assistant_preferences_service: AssistantPreferencesService = Depends(
        get_assistant_preferences_service
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantPreferencesDTO:
    return await assistant_preferences_service.get_preferences(db, current_user.id)


@router.put("/preferences", response_model=AssistantPreferencesDTO)
async def update_my_assistant_preferences(
    payload: AssistantPreferencesUpdateDTO,
    assistant_preferences_service: AssistantPreferencesService = Depends(
        get_assistant_preferences_service
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantPreferencesDTO:
    return await assistant_preferences_service.update_preferences(
        db,
        current_user.id,
        payload,
    )


@router.get("/rules/me", response_model=AssistantRuleProfileDTO)
async def get_my_assistant_rules(
    assistant_rule_service: AssistantRuleService = Depends(get_assistant_rule_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantRuleProfileDTO:
    return await assistant_rule_service.get_user_rules(db, owner_id=current_user.id)


@router.put("/rules/me", response_model=AssistantRuleProfileDTO)
async def update_my_assistant_rules(
    payload: AssistantRuleProfileUpdateDTO,
    assistant_rule_service: AssistantRuleService = Depends(get_assistant_rule_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantRuleProfileDTO:
    return await assistant_rule_service.update_user_rules(
        db,
        payload,
        owner_id=current_user.id,
    )


@router.get("/rules/projects/{project_id}", response_model=AssistantRuleProfileDTO)
async def get_project_assistant_rules(
    project_id: uuid.UUID,
    assistant_rule_service: AssistantRuleService = Depends(get_assistant_rule_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantRuleProfileDTO:
    return await assistant_rule_service.get_project_rules(
        db,
        project_id,
        owner_id=current_user.id,
    )


@router.put("/rules/projects/{project_id}", response_model=AssistantRuleProfileDTO)
async def update_project_assistant_rules(
    project_id: uuid.UUID,
    payload: AssistantRuleProfileUpdateDTO,
    assistant_rule_service: AssistantRuleService = Depends(get_assistant_rule_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantRuleProfileDTO:
    return await assistant_rule_service.update_project_rules(
        db,
        project_id,
        payload,
        owner_id=current_user.id,
    )
