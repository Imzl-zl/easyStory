from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone
import json
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assistant.service import (
    AssistantAgentCreateDTO,
    AssistantAgentDetailDTO,
    AssistantAgentService,
    AssistantAgentSummaryDTO,
    AssistantAgentUpdateDTO,
    AssistantHookCreateDTO,
    AssistantHookDetailDTO,
    AssistantHookService,
    AssistantHookSummaryDTO,
    AssistantHookUpdateDTO,
    AssistantMcpCreateDTO,
    AssistantMcpDetailDTO,
    AssistantMcpService,
    AssistantMcpSummaryDTO,
    AssistantMcpUpdateDTO,
    AssistantPreferencesDTO,
    AssistantPreferencesService,
    AssistantPreferencesUpdateDTO,
    AssistantRuleProfileDTO,
    AssistantRuleProfileUpdateDTO,
    AssistantRuleService,
    AssistantSkillCreateDTO,
    AssistantSkillDetailDTO,
    AssistantSkillService,
    AssistantSkillSummaryDTO,
    AssistantSkillUpdateDTO,
    AssistantService,
    AssistantTurnRequestDTO,
    AssistantTurnResponseDTO,
    resolve_assistant_stream_error_meta,
    create_assistant_preferences_service,
    create_assistant_agent_service,
    create_assistant_hook_service,
    create_assistant_mcp_service,
    create_assistant_rule_service,
    create_assistant_skill_service,
    create_assistant_service,
    resolve_assistant_terminal_payload,
)
from app.modules.assistant.service.assistant_turn_runtime_support import build_turn_run_id
from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.shared.db import get_async_db_session
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])
ASSISTANT_TURN_RESPONSE_SCHEMA = AssistantTurnResponseDTO.model_json_schema()


def get_assistant_service() -> AssistantService:
    return create_assistant_service()


def get_assistant_rule_service() -> AssistantRuleService:
    return create_assistant_rule_service()


def get_assistant_agent_service() -> AssistantAgentService:
    return create_assistant_agent_service()


def get_assistant_preferences_service() -> AssistantPreferencesService:
    return create_assistant_preferences_service()


def get_assistant_hook_service() -> AssistantHookService:
    return create_assistant_hook_service()


def get_assistant_mcp_service() -> AssistantMcpService:
    return create_assistant_mcp_service()


def get_assistant_skill_service() -> AssistantSkillService:
    return create_assistant_skill_service()


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
    except Exception as exc:
        yield _format_sse_event(
            "error",
            _build_assistant_stream_error_payload(
                exc,
                request_payload=payload,
                owner_id=owner_id,
            ),
        )


def _format_sse_event(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _resolve_assistant_stream_error_message(error: Exception) -> str:
    detail = str(error).strip()
    if isinstance(error, ConfigurationError):
        if detail:
            return f"这次回复失败了，请检查模型连接后重试。上游提示：{detail}"
        return "这次回复失败了，请检查模型连接后重试。"
    if isinstance(error, BusinessRuleError):
        if detail:
            return detail
        return "这次回复失败了，请重试。"
    if detail:
        return f"这次回复中断了，请重试。详细信息：{detail}"
    return "这次回复中断了，请重试。"


def _build_assistant_stream_request_meta(
    *,
    request_payload: AssistantTurnRequestDTO,
    owner_id: uuid.UUID,
) -> dict[str, object]:
    return {
        "run_id": str(
            build_turn_run_id(
                owner_id=owner_id,
                project_id=request_payload.project_id,
                conversation_id=request_payload.conversation_id,
                client_turn_id=request_payload.client_turn_id,
            )
        ),
        "conversation_id": request_payload.conversation_id,
        "client_turn_id": request_payload.client_turn_id,
        "event_seq": 1,
        "state_version": 1,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def _build_assistant_stream_error_payload(
    error: Exception,
    *,
    request_payload: AssistantTurnRequestDTO | None = None,
    owner_id: uuid.UUID | None = None,
) -> dict[str, object]:
    terminal_payload = resolve_assistant_terminal_payload(error)
    payload: dict[str, object] = {}
    stream_meta = resolve_assistant_stream_error_meta(error)
    if stream_meta is not None:
        payload.update(stream_meta)
    elif request_payload is not None and owner_id is not None:
        payload.update(
            _build_assistant_stream_request_meta(
                request_payload=request_payload,
                owner_id=owner_id,
            )
        )
    payload["message"] = (
        terminal_payload.message
        if terminal_payload is not None
        else _resolve_assistant_stream_error_message(error)
    )
    if terminal_payload is not None:
        payload["code"] = terminal_payload.code
        payload["terminal_status"] = terminal_payload.terminal_status
        payload["write_effective"] = terminal_payload.write_effective
        return payload
    if isinstance(error, ConfigurationError):
        payload["code"] = "configuration_error"
        payload["terminal_status"] = "failed"
        payload["write_effective"] = False
        return payload
    if isinstance(error, BusinessRuleError):
        payload["code"] = getattr(error, "code", "business_rule_error")
        payload["terminal_status"] = "failed"
        payload["write_effective"] = False
    return payload


@router.get("/preferences", response_model=AssistantPreferencesDTO)
async def get_my_assistant_preferences(
    assistant_preferences_service: AssistantPreferencesService = Depends(
        get_assistant_preferences_service
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantPreferencesDTO:
    return await assistant_preferences_service.get_user_preferences(db, owner_id=current_user.id)


@router.put("/preferences", response_model=AssistantPreferencesDTO)
async def update_my_assistant_preferences(
    payload: AssistantPreferencesUpdateDTO,
    assistant_preferences_service: AssistantPreferencesService = Depends(
        get_assistant_preferences_service
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantPreferencesDTO:
    return await assistant_preferences_service.update_user_preferences(
        db,
        owner_id=current_user.id,
        payload=payload,
    )


@router.get("/preferences/projects/{project_id}", response_model=AssistantPreferencesDTO)
async def get_project_assistant_preferences(
    project_id: uuid.UUID,
    assistant_preferences_service: AssistantPreferencesService = Depends(
        get_assistant_preferences_service
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantPreferencesDTO:
    return await assistant_preferences_service.get_project_preferences(
        db,
        project_id,
        owner_id=current_user.id,
    )


@router.put("/preferences/projects/{project_id}", response_model=AssistantPreferencesDTO)
async def update_project_assistant_preferences(
    project_id: uuid.UUID,
    payload: AssistantPreferencesUpdateDTO,
    assistant_preferences_service: AssistantPreferencesService = Depends(
        get_assistant_preferences_service
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantPreferencesDTO:
    return await assistant_preferences_service.update_project_preferences(
        db,
        project_id,
        owner_id=current_user.id,
        payload=payload,
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


@router.get("/skills", response_model=list[AssistantSkillSummaryDTO])
async def list_my_assistant_skills(
    assistant_skill_service: AssistantSkillService = Depends(get_assistant_skill_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> list[AssistantSkillSummaryDTO]:
    return await assistant_skill_service.list_user_skills(db, owner_id=current_user.id)


@router.get("/skills/projects/{project_id}", response_model=list[AssistantSkillSummaryDTO])
async def list_project_assistant_skills(
    project_id: uuid.UUID,
    assistant_skill_service: AssistantSkillService = Depends(get_assistant_skill_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> list[AssistantSkillSummaryDTO]:
    return await assistant_skill_service.list_project_skills(
        db,
        project_id,
        owner_id=current_user.id,
    )


@router.get("/agents", response_model=list[AssistantAgentSummaryDTO])
async def list_my_assistant_agents(
    assistant_agent_service: AssistantAgentService = Depends(get_assistant_agent_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> list[AssistantAgentSummaryDTO]:
    return await assistant_agent_service.list_user_agents(db, owner_id=current_user.id)


@router.get("/hooks", response_model=list[AssistantHookSummaryDTO])
async def list_my_assistant_hooks(
    assistant_hook_service: AssistantHookService = Depends(get_assistant_hook_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> list[AssistantHookSummaryDTO]:
    return await assistant_hook_service.list_user_hooks(db, owner_id=current_user.id)


@router.get("/mcp_servers", response_model=list[AssistantMcpSummaryDTO])
async def list_my_assistant_mcp_servers(
    assistant_mcp_service: AssistantMcpService = Depends(get_assistant_mcp_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> list[AssistantMcpSummaryDTO]:
    return await assistant_mcp_service.list_user_mcp_servers(db, owner_id=current_user.id)


@router.get("/mcp_servers/projects/{project_id}", response_model=list[AssistantMcpSummaryDTO])
async def list_project_assistant_mcp_servers(
    project_id: uuid.UUID,
    assistant_mcp_service: AssistantMcpService = Depends(get_assistant_mcp_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> list[AssistantMcpSummaryDTO]:
    return await assistant_mcp_service.list_project_mcp_servers(
        db,
        project_id,
        owner_id=current_user.id,
    )


@router.post("/agents", response_model=AssistantAgentDetailDTO)
async def create_my_assistant_agent(
    payload: AssistantAgentCreateDTO,
    assistant_agent_service: AssistantAgentService = Depends(get_assistant_agent_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantAgentDetailDTO:
    return await assistant_agent_service.create_user_agent(
        db,
        payload,
        owner_id=current_user.id,
    )


@router.post("/hooks", response_model=AssistantHookDetailDTO)
async def create_my_assistant_hook(
    payload: AssistantHookCreateDTO,
    assistant_hook_service: AssistantHookService = Depends(get_assistant_hook_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantHookDetailDTO:
    return await assistant_hook_service.create_user_hook(
        db,
        payload,
        owner_id=current_user.id,
    )


@router.post("/mcp_servers", response_model=AssistantMcpDetailDTO)
async def create_my_assistant_mcp_server(
    payload: AssistantMcpCreateDTO,
    assistant_mcp_service: AssistantMcpService = Depends(get_assistant_mcp_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantMcpDetailDTO:
    return await assistant_mcp_service.create_user_mcp_server(
        db,
        payload,
        owner_id=current_user.id,
    )


@router.post("/mcp_servers/projects/{project_id}", response_model=AssistantMcpDetailDTO)
async def create_project_assistant_mcp_server(
    project_id: uuid.UUID,
    payload: AssistantMcpCreateDTO,
    assistant_mcp_service: AssistantMcpService = Depends(get_assistant_mcp_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantMcpDetailDTO:
    return await assistant_mcp_service.create_project_mcp_server(
        db,
        project_id,
        payload,
        owner_id=current_user.id,
    )


@router.get("/agents/{agent_id}", response_model=AssistantAgentDetailDTO)
async def get_my_assistant_agent(
    agent_id: str,
    assistant_agent_service: AssistantAgentService = Depends(get_assistant_agent_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantAgentDetailDTO:
    return await assistant_agent_service.get_user_agent(
        db,
        agent_id,
        owner_id=current_user.id,
    )


@router.get("/hooks/{hook_id}", response_model=AssistantHookDetailDTO)
async def get_my_assistant_hook(
    hook_id: str,
    assistant_hook_service: AssistantHookService = Depends(get_assistant_hook_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantHookDetailDTO:
    return await assistant_hook_service.get_user_hook(
        db,
        hook_id,
        owner_id=current_user.id,
    )


@router.get("/mcp_servers/projects/{project_id}/{server_id}", response_model=AssistantMcpDetailDTO)
async def get_project_assistant_mcp_server(
    project_id: uuid.UUID,
    server_id: str,
    assistant_mcp_service: AssistantMcpService = Depends(get_assistant_mcp_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantMcpDetailDTO:
    return await assistant_mcp_service.get_project_mcp_server(
        db,
        project_id,
        server_id,
        owner_id=current_user.id,
    )


@router.get("/mcp_servers/{server_id}", response_model=AssistantMcpDetailDTO)
async def get_my_assistant_mcp_server(
    server_id: str,
    assistant_mcp_service: AssistantMcpService = Depends(get_assistant_mcp_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantMcpDetailDTO:
    return await assistant_mcp_service.get_user_mcp_server(
        db,
        server_id,
        owner_id=current_user.id,
    )


@router.put("/agents/{agent_id}", response_model=AssistantAgentDetailDTO)
async def update_my_assistant_agent(
    agent_id: str,
    payload: AssistantAgentUpdateDTO,
    assistant_agent_service: AssistantAgentService = Depends(get_assistant_agent_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantAgentDetailDTO:
    return await assistant_agent_service.update_user_agent(
        db,
        agent_id,
        payload,
        owner_id=current_user.id,
    )


@router.put("/hooks/{hook_id}", response_model=AssistantHookDetailDTO)
async def update_my_assistant_hook(
    hook_id: str,
    payload: AssistantHookUpdateDTO,
    assistant_hook_service: AssistantHookService = Depends(get_assistant_hook_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantHookDetailDTO:
    return await assistant_hook_service.update_user_hook(
        db,
        hook_id,
        payload,
        owner_id=current_user.id,
    )


@router.put("/mcp_servers/{server_id}", response_model=AssistantMcpDetailDTO)
async def update_my_assistant_mcp_server(
    server_id: str,
    payload: AssistantMcpUpdateDTO,
    assistant_mcp_service: AssistantMcpService = Depends(get_assistant_mcp_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantMcpDetailDTO:
    return await assistant_mcp_service.update_user_mcp_server(
        db,
        server_id,
        payload,
        owner_id=current_user.id,
    )


@router.put("/mcp_servers/projects/{project_id}/{server_id}", response_model=AssistantMcpDetailDTO)
async def update_project_assistant_mcp_server(
    project_id: uuid.UUID,
    server_id: str,
    payload: AssistantMcpUpdateDTO,
    assistant_mcp_service: AssistantMcpService = Depends(get_assistant_mcp_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantMcpDetailDTO:
    return await assistant_mcp_service.update_project_mcp_server(
        db,
        project_id,
        server_id,
        payload,
        owner_id=current_user.id,
    )


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_my_assistant_agent(
    agent_id: str,
    assistant_agent_service: AssistantAgentService = Depends(get_assistant_agent_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> None:
    await assistant_agent_service.delete_user_agent(
        db,
        agent_id,
        owner_id=current_user.id,
    )


@router.delete("/hooks/{hook_id}", status_code=204)
async def delete_my_assistant_hook(
    hook_id: str,
    assistant_hook_service: AssistantHookService = Depends(get_assistant_hook_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> None:
    await assistant_hook_service.delete_user_hook(
        db,
        hook_id,
        owner_id=current_user.id,
    )


@router.delete("/mcp_servers/{server_id}", status_code=204)
async def delete_my_assistant_mcp_server(
    server_id: str,
    assistant_mcp_service: AssistantMcpService = Depends(get_assistant_mcp_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> None:
    await assistant_mcp_service.delete_user_mcp_server(
        db,
        server_id,
        owner_id=current_user.id,
    )


@router.delete("/mcp_servers/projects/{project_id}/{server_id}", status_code=204)
async def delete_project_assistant_mcp_server(
    project_id: uuid.UUID,
    server_id: str,
    assistant_mcp_service: AssistantMcpService = Depends(get_assistant_mcp_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> None:
    await assistant_mcp_service.delete_project_mcp_server(
        db,
        project_id,
        server_id,
        owner_id=current_user.id,
    )


@router.post("/skills", response_model=AssistantSkillDetailDTO)
async def create_my_assistant_skill(
    payload: AssistantSkillCreateDTO,
    assistant_skill_service: AssistantSkillService = Depends(get_assistant_skill_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantSkillDetailDTO:
    return await assistant_skill_service.create_user_skill(
        db,
        payload,
        owner_id=current_user.id,
    )


@router.post("/skills/projects/{project_id}", response_model=AssistantSkillDetailDTO)
async def create_project_assistant_skill(
    project_id: uuid.UUID,
    payload: AssistantSkillCreateDTO,
    assistant_skill_service: AssistantSkillService = Depends(get_assistant_skill_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantSkillDetailDTO:
    return await assistant_skill_service.create_project_skill(
        db,
        project_id,
        payload,
        owner_id=current_user.id,
    )


@router.get("/skills/projects/{project_id}/{skill_id}", response_model=AssistantSkillDetailDTO)
async def get_project_assistant_skill(
    project_id: uuid.UUID,
    skill_id: str,
    assistant_skill_service: AssistantSkillService = Depends(get_assistant_skill_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantSkillDetailDTO:
    return await assistant_skill_service.get_project_skill(
        db,
        project_id,
        skill_id,
        owner_id=current_user.id,
    )


@router.get("/skills/{skill_id}", response_model=AssistantSkillDetailDTO)
async def get_my_assistant_skill(
    skill_id: str,
    assistant_skill_service: AssistantSkillService = Depends(get_assistant_skill_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantSkillDetailDTO:
    return await assistant_skill_service.get_user_skill(
        db,
        skill_id,
        owner_id=current_user.id,
    )


@router.put("/skills/{skill_id}", response_model=AssistantSkillDetailDTO)
async def update_my_assistant_skill(
    skill_id: str,
    payload: AssistantSkillUpdateDTO,
    assistant_skill_service: AssistantSkillService = Depends(get_assistant_skill_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantSkillDetailDTO:
    return await assistant_skill_service.update_user_skill(
        db,
        skill_id,
        payload,
        owner_id=current_user.id,
    )


@router.put("/skills/projects/{project_id}/{skill_id}", response_model=AssistantSkillDetailDTO)
async def update_project_assistant_skill(
    project_id: uuid.UUID,
    skill_id: str,
    payload: AssistantSkillUpdateDTO,
    assistant_skill_service: AssistantSkillService = Depends(get_assistant_skill_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AssistantSkillDetailDTO:
    return await assistant_skill_service.update_project_skill(
        db,
        project_id,
        skill_id,
        payload,
        owner_id=current_user.id,
    )


@router.delete("/skills/{skill_id}", status_code=204)
async def delete_my_assistant_skill(
    skill_id: str,
    assistant_skill_service: AssistantSkillService = Depends(get_assistant_skill_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> None:
    await assistant_skill_service.delete_user_skill(
        db,
        skill_id,
        owner_id=current_user.id,
    )


@router.delete("/skills/projects/{project_id}/{skill_id}", status_code=204)
async def delete_project_assistant_skill(
    project_id: uuid.UUID,
    skill_id: str,
    assistant_skill_service: AssistantSkillService = Depends(get_assistant_skill_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> None:
    await assistant_skill_service.delete_project_skill(
        db,
        project_id,
        skill_id,
        owner_id=current_user.id,
    )
