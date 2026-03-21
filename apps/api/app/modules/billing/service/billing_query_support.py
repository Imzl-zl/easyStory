from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from math import ceil

from app.modules.billing.models import TokenUsage
from app.modules.billing.service.dto import (
    BillingUsageBreakdownDTO,
    BudgetStatusDTO,
    BudgetStatusViewDTO,
    TokenUsageViewDTO,
)
from app.modules.config_registry.schemas.config_schemas import BudgetConfig
from app.modules.workflow.models import WorkflowExecution

ZERO_TOKENS = 0
ZERO_COST = Decimal("0")
SUMMARY_USAGE_ORDER = {
    "generate": 0,
    "review": 1,
    "fix": 2,
    "analysis": 3,
    "dry_run": 4,
}


def build_usage_breakdowns(usages: list[TokenUsage]) -> list[BillingUsageBreakdownDTO]:
    grouped: dict[str, dict[str, int | Decimal]] = defaultdict(
        lambda: {
            "call_count": 0,
            "input_tokens": ZERO_TOKENS,
            "output_tokens": ZERO_TOKENS,
            "estimated_cost": ZERO_COST,
        }
    )
    for usage in usages:
        group = grouped[usage.usage_type]
        group["call_count"] += 1
        group["input_tokens"] += usage.input_tokens
        group["output_tokens"] += usage.output_tokens
        group["estimated_cost"] += usage.estimated_cost
    return [
        BillingUsageBreakdownDTO(
            usage_type=usage_type,  # type: ignore[arg-type]
            call_count=int(group["call_count"]),
            input_tokens=int(group["input_tokens"]),
            output_tokens=int(group["output_tokens"]),
            total_tokens=int(group["input_tokens"]) + int(group["output_tokens"]),
            estimated_cost=group["estimated_cost"],  # type: ignore[arg-type]
        )
        for usage_type, group in sorted(
            grouped.items(),
            key=lambda item: SUMMARY_USAGE_ORDER.get(item[0], len(SUMMARY_USAGE_ORDER)),
        )
    ]


def load_budget_config(workflow: WorkflowExecution) -> BudgetConfig:
    snapshot = workflow.workflow_snapshot or {}
    return BudgetConfig.model_validate(snapshot.get("budget") or {})


def build_budget_status(
    *,
    scope: str,
    used_tokens: int,
    limit_tokens: int,
    warning_threshold: float,
) -> BudgetStatusDTO:
    warning_limit = max(1, ceil(limit_tokens * warning_threshold))
    return BudgetStatusDTO(
        scope=scope,  # type: ignore[arg-type]
        used_tokens=used_tokens,
        limit_tokens=limit_tokens,
        warning_threshold=warning_threshold,
        warning_reached=used_tokens >= warning_limit,
        exceeded=used_tokens > limit_tokens,
    )


def to_budget_status_view(status: BudgetStatusDTO) -> BudgetStatusViewDTO:
    return BudgetStatusViewDTO(
        scope=status.scope,  # type: ignore[arg-type]
        used_tokens=status.used_tokens,
        limit_tokens=status.limit_tokens,
        warning_threshold=status.warning_threshold,
        warning_reached=status.warning_reached,
        exceeded=status.exceeded,
    )


def to_token_usage_view(usage: TokenUsage) -> TokenUsageViewDTO:
    return TokenUsageViewDTO(
        id=usage.id,
        node_execution_id=usage.node_execution_id,
        usage_type=usage.usage_type,  # type: ignore[arg-type]
        model_name=usage.model_name,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.input_tokens + usage.output_tokens,
        estimated_cost=usage.estimated_cost,
        created_at=usage.created_at,
    )


def day_window(recorded_at: datetime) -> tuple[datetime, datetime]:
    start_at = recorded_at.astimezone(timezone.utc).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    return start_at, start_at + timedelta(days=1)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
