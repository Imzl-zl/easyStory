from __future__ import annotations

from datetime import datetime
import uuid
from typing import Literal

from pydantic import BaseModel

from app.modules.review.engine.contracts import ReviewIssue

ReviewStatus = Literal["passed", "failed", "warning"]


class ReviewStatusSummaryDTO(BaseModel):
    passed: int
    failed: int
    warning: int


class ReviewIssueSummaryDTO(BaseModel):
    total: int
    critical: int
    major: int
    minor: int
    suggestion: int


class ReviewTypeSummaryDTO(BaseModel):
    review_type: str
    action_count: int
    statuses: ReviewStatusSummaryDTO
    issues: ReviewIssueSummaryDTO


class WorkflowReviewSummaryDTO(BaseModel):
    workflow_execution_id: uuid.UUID
    project_id: uuid.UUID
    workflow_status: str
    reviewed_node_count: int
    total_actions: int
    last_reviewed_at: datetime | None
    statuses: ReviewStatusSummaryDTO
    issues: ReviewIssueSummaryDTO
    review_types: list[ReviewTypeSummaryDTO]


class WorkflowReviewActionDTO(BaseModel):
    id: uuid.UUID
    node_execution_id: uuid.UUID
    node_id: str
    node_type: str
    node_order: int
    sequence: int
    agent_id: str
    reviewer_name: str | None
    review_type: str
    status: ReviewStatus
    score: float | None
    summary: str | None
    issue_count: int
    issues: list[ReviewIssue]
    execution_time_ms: int | None
    tokens_used: int | None
    created_at: datetime
