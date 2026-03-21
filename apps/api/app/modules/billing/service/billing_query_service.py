from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from math import ceil
from typing import Callable
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from app.modules.billing.models import TokenUsage
from app.modules.billing.service.dto import (
    BillingUsageBreakdownDTO,
    BudgetStatusDTO,
    BudgetStatusViewDTO,
    TokenUsageViewDTO,
    UsageType,
    WorkflowBillingSummaryDTO,
)
from app.modules.config_registry.schemas.config_schemas import BudgetConfig
from app.modules.project.models import Project
from app.modules.workflow.models import NodeExecution, WorkflowExecution
from app.shared.runtime.errors import NotFoundError

ZERO_TOKENS = 0
ZERO_COST = Decimal("0")
SUMMARY_USAGE_ORDER = {
    "generate": 0,
    "review": 1,
    "fix": 2,
    "analysis": 3,
    "dry_run": 4,
}


class BillingQueryService:
    def __init__(
        self,
        *,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self.now_factory = now_factory or self._utc_now

    def get_workflow_summary(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowBillingSummaryDTO:
        workflow = self._require_owned_workflow(db, workflow_id, owner_id=owner_id)
        usages = self._workflow_usage_query(db, workflow.id).all()
        usage_by_type = self._build_usage_breakdowns(usages)
        total_input_tokens = sum(item.input_tokens for item in usage_by_type)
        total_output_tokens = sum(item.output_tokens for item in usage_by_type)
        budget_config = self._load_budget_config(workflow)
        return WorkflowBillingSummaryDTO(
            workflow_execution_id=workflow.id,
            project_id=workflow.project_id,
            workflow_status=workflow.status,
            on_exceed=budget_config.on_exceed,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_tokens=total_input_tokens + total_output_tokens,
            total_estimated_cost=sum(
                (item.estimated_cost for item in usage_by_type),
                start=ZERO_COST,
            ),
            usage_by_type=usage_by_type,
            budget_statuses=self._build_budget_status_views(
                db,
                workflow,
                owner_id=owner_id,
                budget_config=budget_config,
            ),
        )

    def list_workflow_token_usages(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        usage_type: UsageType | None = None,
        limit: int = 100,
    ) -> list[TokenUsageViewDTO]:
        workflow = self._require_owned_workflow(db, workflow_id, owner_id=owner_id)
        query = self._workflow_usage_query(db, workflow.id)
        if usage_type is not None:
            query = query.filter(TokenUsage.usage_type == usage_type)
        usages = query.order_by(TokenUsage.created_at.desc(), TokenUsage.id.desc()).limit(limit).all()
        return [self._to_token_usage_view(item) for item in usages]

    def _workflow_usage_query(
        self,
        db: Session,
        workflow_id: uuid.UUID,
    ) -> Query[TokenUsage]:
        return (
            db.query(TokenUsage)
            .join(NodeExecution, TokenUsage.node_execution_id == NodeExecution.id)
            .filter(NodeExecution.workflow_execution_id == workflow_id)
        )

    def _build_usage_breakdowns(
        self,
        usages: list[TokenUsage],
    ) -> list[BillingUsageBreakdownDTO]:
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

    def _build_budget_status_views(
        self,
        db: Session,
        workflow: WorkflowExecution,
        *,
        owner_id: uuid.UUID,
        budget_config: BudgetConfig,
    ) -> list[BudgetStatusViewDTO]:
        recorded_at = self.now_factory()
        start_at, end_at = self._day_window(recorded_at)
        statuses = [
            self._build_budget_status(
                scope="workflow",
                used_tokens=self._sum_workflow_tokens(db, workflow.id),
                limit_tokens=budget_config.max_tokens_per_workflow,
                warning_threshold=budget_config.warning_threshold,
            ),
            self._build_budget_status(
                scope="project_day",
                used_tokens=self._sum_project_daily_tokens(db, workflow.project_id, start_at, end_at),
                limit_tokens=budget_config.max_tokens_per_day,
                warning_threshold=budget_config.warning_threshold,
            ),
        ]
        if budget_config.max_tokens_per_day_per_user is not None:
            statuses.append(
                self._build_budget_status(
                    scope="user_day",
                    used_tokens=self._sum_user_daily_tokens(db, owner_id, start_at, end_at),
                    limit_tokens=budget_config.max_tokens_per_day_per_user,
                    warning_threshold=budget_config.warning_threshold,
                )
            )
        return [self._to_budget_status_view(item) for item in statuses]

    def _sum_workflow_tokens(self, db: Session, workflow_id: uuid.UUID) -> int:
        query = self._workflow_usage_query(db, workflow_id)
        return self._sum_tokens(query)

    def _sum_project_daily_tokens(
        self,
        db: Session,
        project_id: uuid.UUID,
        start_at: datetime,
        end_at: datetime,
    ) -> int:
        query = (
            db.query(TokenUsage)
            .filter(TokenUsage.project_id == project_id)
            .filter(TokenUsage.created_at >= start_at, TokenUsage.created_at < end_at)
        )
        return self._sum_tokens(query)

    def _sum_user_daily_tokens(
        self,
        db: Session,
        owner_id: uuid.UUID,
        start_at: datetime,
        end_at: datetime,
    ) -> int:
        query = (
            db.query(TokenUsage)
            .join(Project, TokenUsage.project_id == Project.id)
            .filter(Project.owner_id == owner_id)
            .filter(TokenUsage.created_at >= start_at, TokenUsage.created_at < end_at)
        )
        return self._sum_tokens(query)

    def _sum_tokens(self, query: Query[TokenUsage]) -> int:
        total = query.with_entities(
            func.coalesce(func.sum(TokenUsage.input_tokens + TokenUsage.output_tokens), ZERO_TOKENS)
        ).scalar()
        return int(total or ZERO_TOKENS)

    def _require_owned_workflow(
        self,
        db: Session,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowExecution:
        workflow = (
            db.query(WorkflowExecution)
            .join(Project, WorkflowExecution.project_id == Project.id)
            .filter(
                WorkflowExecution.id == workflow_id,
                Project.owner_id == owner_id,
            )
            .one_or_none()
        )
        if workflow is None:
            raise NotFoundError(f"Workflow execution not found: {workflow_id}")
        return workflow

    def _load_budget_config(self, workflow: WorkflowExecution) -> BudgetConfig:
        snapshot = workflow.workflow_snapshot or {}
        return BudgetConfig.model_validate(snapshot.get("budget") or {})

    def _build_budget_status(
        self,
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

    def _to_budget_status_view(
        self,
        status: BudgetStatusDTO,
    ) -> BudgetStatusViewDTO:
        return BudgetStatusViewDTO(
            scope=status.scope,  # type: ignore[arg-type]
            used_tokens=status.used_tokens,
            limit_tokens=status.limit_tokens,
            warning_threshold=status.warning_threshold,
            warning_reached=status.warning_reached,
            exceeded=status.exceeded,
        )

    def _to_token_usage_view(self, usage: TokenUsage) -> TokenUsageViewDTO:
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

    def _day_window(self, recorded_at: datetime) -> tuple[datetime, datetime]:
        start_at = recorded_at.astimezone(timezone.utc).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        return start_at, start_at + timedelta(days=1)

    def _utc_now(self) -> datetime:
        return datetime.now(timezone.utc)
