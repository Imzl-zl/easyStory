from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import selectinload

from app.modules.observability.models import ExecutionLog, PromptReplay
from app.modules.workflow.models import NodeExecution

TERMINAL_WORKFLOW_STATUSES = frozenset({"completed", "failed", "cancelled"})


def build_after_cursor(
    after_created_at: datetime,
    after_id: uuid.UUID | None,
):
    if after_id is None:
        return ExecutionLog.created_at > after_created_at
    return or_(
        ExecutionLog.created_at > after_created_at,
        and_(
            ExecutionLog.created_at == after_created_at,
            ExecutionLog.id > after_id,
        ),
    )


def build_node_execution_statement(
    workflow_id: uuid.UUID,
    *,
    node_id: str | None,
    status: str | None,
):
    statement = (
        select(NodeExecution)
        .options(
            selectinload(NodeExecution.artifacts),
            selectinload(NodeExecution.review_actions),
        )
        .where(NodeExecution.workflow_execution_id == workflow_id)
    )
    if node_id is not None:
        statement = statement.where(NodeExecution.node_id == node_id)
    if status is not None:
        statement = statement.where(NodeExecution.status == status)
    return statement.order_by(NodeExecution.node_order.asc(), NodeExecution.sequence.asc())


def build_execution_log_statement(
    workflow_id: uuid.UUID,
    *,
    level: str | None,
    node_execution_id: uuid.UUID | None,
):
    statement = select(ExecutionLog).where(ExecutionLog.workflow_execution_id == workflow_id)
    if level is not None:
        statement = statement.where(ExecutionLog.level == level)
    if node_execution_id is not None:
        statement = statement.where(ExecutionLog.node_execution_id == node_execution_id)
    return statement


def build_prompt_replay_statement(
    node_execution_id: uuid.UUID,
    *,
    replay_type: str | None,
):
    statement = select(PromptReplay).where(PromptReplay.node_execution_id == node_execution_id)
    if replay_type is not None:
        statement = statement.where(PromptReplay.replay_type == replay_type)
    return statement.order_by(PromptReplay.created_at.asc())
