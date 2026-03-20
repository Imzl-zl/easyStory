from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import uuid
from typing import Literal

UsageType = Literal["generate", "review", "fix", "analysis", "dry_run"]
BudgetScope = Literal["node", "workflow", "project_day", "user_day"]


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
