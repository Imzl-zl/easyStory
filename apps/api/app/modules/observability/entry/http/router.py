from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.modules.observability.service import (
    ExecutionLogViewDTO,
    NodeExecutionViewDTO,
    PromptReplayViewDTO,
    WorkflowObservabilityService,
    create_workflow_observability_service,
)
from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.shared.db import get_db_session

router = APIRouter(tags=["observability"])


def get_workflow_observability_service() -> WorkflowObservabilityService:
    return create_workflow_observability_service()


@router.get(
    "/api/v1/workflows/{workflow_id}/executions",
    response_model=list[NodeExecutionViewDTO],
)
def list_workflow_executions(
    workflow_id: uuid.UUID,
    observability_service: WorkflowObservabilityService = Depends(get_workflow_observability_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[NodeExecutionViewDTO]:
    return observability_service.list_node_executions(
        db,
        workflow_id,
        owner_id=current_user.id,
    )


@router.get(
    "/api/v1/workflows/{workflow_id}/logs",
    response_model=list[ExecutionLogViewDTO],
)
def list_workflow_logs(
    workflow_id: uuid.UUID,
    level: Literal["INFO", "WARNING", "ERROR"] | None = Query(default=None),
    limit: int = Query(default=50, ge=1),
    observability_service: WorkflowObservabilityService = Depends(get_workflow_observability_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[ExecutionLogViewDTO]:
    return observability_service.list_execution_logs(
        db,
        workflow_id,
        owner_id=current_user.id,
        level=level,
        limit=limit,
    )


@router.get(
    "/api/v1/workflows/{workflow_id}/node-executions/{node_execution_id}/prompt-replays",
    response_model=list[PromptReplayViewDTO],
)
def list_prompt_replays(
    workflow_id: uuid.UUID,
    node_execution_id: uuid.UUID,
    observability_service: WorkflowObservabilityService = Depends(get_workflow_observability_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[PromptReplayViewDTO]:
    return observability_service.list_prompt_replays(
        db,
        workflow_id,
        node_execution_id,
        owner_id=current_user.id,
    )
