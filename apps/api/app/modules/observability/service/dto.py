from __future__ import annotations

from datetime import datetime
import uuid
from typing import Any

from pydantic import BaseModel


class ArtifactViewDTO(BaseModel):
    id: uuid.UUID
    artifact_type: str
    content_version_id: uuid.UUID | None
    payload: dict[str, Any] | None
    word_count: int | None
    created_at: datetime


class AuditLogViewDTO(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    event_type: str
    entity_type: str
    entity_id: uuid.UUID
    details: dict[str, Any] | None
    created_at: datetime


class ReviewActionViewDTO(BaseModel):
    id: uuid.UUID
    agent_id: str
    reviewer_name: str | None
    review_type: str
    status: str
    score: float | None
    summary: str | None
    issues: list[dict[str, Any]] | dict[str, Any] | None
    execution_time_ms: int | None
    tokens_used: int | None
    created_at: datetime


class NodeExecutionViewDTO(BaseModel):
    id: uuid.UUID
    workflow_execution_id: uuid.UUID
    node_id: str
    sequence: int
    node_order: int
    node_type: str
    status: str
    input_summary: dict[str, Any]
    context_report: dict[str, Any] | None
    output_data: dict[str, Any] | None
    retry_count: int
    error_message: str | None
    execution_time_ms: int | None
    started_at: datetime | None
    completed_at: datetime | None
    artifacts: list[ArtifactViewDTO]
    review_actions: list[ReviewActionViewDTO]


class ExecutionLogViewDTO(BaseModel):
    id: uuid.UUID
    workflow_execution_id: uuid.UUID
    node_execution_id: uuid.UUID | None
    level: str
    message: str
    details: dict[str, Any] | None
    created_at: datetime


class PromptReplayViewDTO(BaseModel):
    id: uuid.UUID
    node_execution_id: uuid.UUID
    replay_type: str
    model_name: str
    prompt_text: str
    response_text: str | None
    input_tokens: int | None
    output_tokens: int | None
    created_at: datetime
