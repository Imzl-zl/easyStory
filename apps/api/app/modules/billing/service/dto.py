from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import uuid
from typing import Literal

from pydantic import BaseModel

UsageType = Literal["generate", "review", "fix", "analysis", "dry_run"]
BudgetScope = Literal["node", "workflow", "project_day", "user_day"]
WorkflowBillingScope = Literal["workflow", "project_day", "user_day"]


@dataclass(frozen=True)
class TokenUsageRecordDTO:
    token_usage_id: uuid.UUID
    project_id: uuid.UUID
    node_execution_id: uuid.UUID | None
    credential_id: uuid.UUID
    usage_type: UsageType
    model_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: Decimal


@dataclass(frozen=True)
class BudgetStatusDTO:
    scope: BudgetScope
    used_tokens: int
    limit_tokens: int
    warning_threshold: float
    warning_reached: bool
    exceeded: bool


@dataclass(frozen=True)
class BudgetCheckResultDTO:
    usage: TokenUsageRecordDTO
    statuses: tuple[BudgetStatusDTO, ...]
    exceeded_status: BudgetStatusDTO | None


class TokenUsageViewDTO(BaseModel):
    id: uuid.UUID
    workflow_execution_id: uuid.UUID | None
    node_execution_id: uuid.UUID | None
    usage_type: UsageType
    model_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: Decimal
    created_at: datetime


class BillingUsageBreakdownDTO(BaseModel):
    usage_type: UsageType
    call_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: Decimal


class BudgetStatusViewDTO(BaseModel):
    scope: WorkflowBillingScope
    used_tokens: int
    limit_tokens: int
    warning_threshold: float
    warning_reached: bool
    exceeded: bool


class WorkflowBillingSummaryDTO(BaseModel):
    workflow_execution_id: uuid.UUID
    project_id: uuid.UUID
    workflow_status: str
    on_exceed: Literal["pause", "skip", "fail"]
    budget_recorded_at: datetime
    budget_window_start_at: datetime
    budget_window_end_at: datetime
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_estimated_cost: Decimal
    usage_by_type: list[BillingUsageBreakdownDTO]
    budget_statuses: list[BudgetStatusViewDTO]
