from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import AsyncIterator
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.modules.observability.service import (
    ExecutionLogViewDTO,
    NodeExecutionViewDTO,
    PromptReplayViewDTO,
    WorkflowObservabilityService,
    create_workflow_observability_service,
)
from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.shared.db import AsyncSessionFactory, get_async_db_session, get_async_session_factory

router = APIRouter(tags=["observability"])


async def get_workflow_observability_service() -> WorkflowObservabilityService:
    return create_workflow_observability_service()


@router.get(
    "/api/v1/workflows/{workflow_id}/executions",
    response_model=list[NodeExecutionViewDTO],
)
async def list_workflow_executions(
    workflow_id: uuid.UUID,
    node_id: str | None = Query(default=None, min_length=1),
    status: str | None = Query(default=None, min_length=1),
    observability_service: WorkflowObservabilityService = Depends(get_workflow_observability_service),
    current_user: User = Depends(get_current_user),
    db=Depends(get_async_db_session),
) -> list[NodeExecutionViewDTO]:
    return await observability_service.list_node_executions(
        db,
        workflow_id,
        owner_id=current_user.id,
        node_id=node_id,
        status=status,
    )


@router.get(
    "/api/v1/workflows/{workflow_id}/logs",
    response_model=list[ExecutionLogViewDTO],
)
async def list_workflow_logs(
    workflow_id: uuid.UUID,
    level: Literal["INFO", "WARNING", "ERROR"] | None = Query(default=None),
    node_execution_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1),
    observability_service: WorkflowObservabilityService = Depends(get_workflow_observability_service),
    current_user: User = Depends(get_current_user),
    db=Depends(get_async_db_session),
) -> list[ExecutionLogViewDTO]:
    return await observability_service.list_execution_logs(
        db,
        workflow_id,
        owner_id=current_user.id,
        level=level,
        node_execution_id=node_execution_id,
        limit=limit,
    )


@router.get("/api/v1/workflows/{workflow_id}/events")
async def stream_workflow_events(
    workflow_id: uuid.UUID,
    request: Request,
    level: Literal["INFO", "WARNING", "ERROR"] | None = Query(default=None),
    node_execution_id: uuid.UUID | None = Query(default=None),
    timeout_seconds: int = Query(default=15, ge=1, le=300),
    poll_interval_ms: int = Query(default=500, ge=100, le=5000),
    observability_service: WorkflowObservabilityService = Depends(get_workflow_observability_service),
    current_user: User = Depends(get_current_user),
    session_factory: AsyncSessionFactory = Depends(get_async_session_factory),
) -> StreamingResponse:
    async with session_factory() as session:
        await observability_service.list_execution_logs(
            session,
            workflow_id,
            owner_id=current_user.id,
            level=level,
            node_execution_id=node_execution_id,
            limit=1,
        )

    return StreamingResponse(
        _iter_workflow_events(
            request=request,
            workflow_id=workflow_id,
            owner_id=current_user.id,
            level=level,
            node_execution_id=node_execution_id,
            timeout_seconds=timeout_seconds,
            poll_interval_ms=poll_interval_ms,
            observability_service=observability_service,
            session_factory=session_factory,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/api/v1/workflows/{workflow_id}/node-executions/{node_execution_id}/prompt-replays",
    response_model=list[PromptReplayViewDTO],
)
async def list_prompt_replays(
    workflow_id: uuid.UUID,
    node_execution_id: uuid.UUID,
    replay_type: str | None = Query(default=None, min_length=1),
    observability_service: WorkflowObservabilityService = Depends(get_workflow_observability_service),
    current_user: User = Depends(get_current_user),
    db=Depends(get_async_db_session),
) -> list[PromptReplayViewDTO]:
    return await observability_service.list_prompt_replays(
        db,
        workflow_id,
        node_execution_id,
        owner_id=current_user.id,
        replay_type=replay_type,
    )


async def _iter_workflow_events(
    *,
    request: Request,
    workflow_id: uuid.UUID,
    owner_id: uuid.UUID,
    level: Literal["INFO", "WARNING", "ERROR"] | None,
    node_execution_id: uuid.UUID | None,
    timeout_seconds: int,
    poll_interval_ms: int,
    observability_service: WorkflowObservabilityService,
    session_factory: AsyncSessionFactory,
) -> AsyncIterator[str]:
    deadline = time.monotonic() + timeout_seconds
    last_created_at = None
    last_log_id = None
    while time.monotonic() < deadline:
        if await request.is_disconnected():
            break
        async with session_factory() as session:
            logs = await observability_service.list_execution_logs_since(
                session,
                workflow_id,
                owner_id=owner_id,
                after_created_at=last_created_at,
                after_id=last_log_id,
                level=level,
                node_execution_id=node_execution_id,
            )
            is_terminal = await observability_service.is_workflow_terminal(
                session,
                workflow_id,
                owner_id=owner_id,
            )
        if logs:
            for log in logs:
                yield _format_sse_event(
                    event="execution_log",
                    data=log.model_dump(mode="json"),
                    event_id=str(log.id),
                )
            last_created_at = logs[-1].created_at
            last_log_id = logs[-1].id
            continue
        yield ": keep-alive\n\n"
        if is_terminal:
            yield _format_sse_event(event="end", data={"workflow_id": str(workflow_id)})
            break
        await asyncio.sleep(poll_interval_ms / 1000)


def _format_sse_event(
    *,
    event: str,
    data: dict,
    event_id: str | None = None,
) -> str:
    lines: list[str] = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data, ensure_ascii=False)}")
    return "\n".join(lines) + "\n\n"
