from __future__ import annotations

from datetime import datetime
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict

WorkflowExecutionStatus = Literal[
    "created",
    "running",
    "paused",
    "failed",
    "completed",
    "cancelled",
]


class WorkflowStartDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str | None = None


class WorkflowPauseDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: Literal[
        "user_request",
        "user_interrupted",
        "budget_exceeded",
        "review_failed",
        "error",
        "loop_pause",
        "max_chapters_reached",
    ] = "user_request"


class WorkflowNodeSummaryDTO(BaseModel):
    id: str
    name: str
    node_type: str
    depends_on: list[str]


class WorkflowExecutionDTO(BaseModel):
    execution_id: uuid.UUID
    project_id: uuid.UUID
    template_id: uuid.UUID | None
    workflow_id: str | None
    workflow_name: str | None
    workflow_version: str | None
    mode: Literal["manual", "auto"] | None
    status: WorkflowExecutionStatus
    current_node_id: str | None
    current_node_name: str | None
    pause_reason: str | None
    resume_from_node: str | None
    has_runtime_snapshot: bool
    started_at: datetime | None
    completed_at: datetime | None
    nodes: list[WorkflowNodeSummaryDTO]


class WorkflowExecutionSummaryDTO(BaseModel):
    execution_id: uuid.UUID
    project_id: uuid.UUID
    template_id: uuid.UUID | None
    workflow_id: str | None
    workflow_name: str | None
    workflow_version: str | None
    mode: Literal["manual", "auto"] | None
    status: WorkflowExecutionStatus
    current_node_id: str | None
    current_node_name: str | None
    pause_reason: str | None
    resume_from_node: str | None
    has_runtime_snapshot: bool
    started_at: datetime | None
    completed_at: datetime | None
