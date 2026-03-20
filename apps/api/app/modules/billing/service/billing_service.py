from __future__ import annotations

from math import ceil
from datetime import datetime, timedelta, timezone
from typing import Callable
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from app.modules.billing.models import TokenUsage
from app.modules.billing.service.dto import (
    BudgetCheckResultDTO,
    BudgetStatusDTO,
    TokenUsageRecordDTO,
    UsageType,
)
from app.modules.config_registry.schemas.config_schemas import BudgetConfig
from app.modules.project.models import Project
from app.modules.workflow.models import NodeExecution
from app.shared.runtime import ModelPricing
from app.shared.runtime.errors import ConfigurationError

SUPPORTED_USAGE_TYPES = frozenset({"generate", "review", "fix", "analysis", "dry_run"})
ZERO_TOKENS = 0


class BillingService:
    def __init__(
        self,
        *,
        model_pricing: ModelPricing,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self.model_pricing = model_pricing
        self.now_factory = now_factory or self._utc_now

    def record_usage_and_check_budget(
        self,
        db: Session,
        *,
        workflow_execution_id: uuid.UUID,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        node_execution_id: uuid.UUID | None,
        credential_id: uuid.UUID,
        usage_type: UsageType,
        model_name: str,
        input_tokens: int | None,
        output_tokens: int | None,
        budget_config: BudgetConfig,
    ) -> BudgetCheckResultDTO:
        recorded_at = self.now_factory()
        normalized_input, normalized_output = self._normalize_usage_tokens(
            usage_type=usage_type,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        usage = self._create_token_usage(
            db,
            project_id=project_id,
            node_execution_id=node_execution_id,
            credential_id=credential_id,
            usage_type=usage_type,
            model_name=model_name,
            input_tokens=normalized_input,
            output_tokens=normalized_output,
            recorded_at=recorded_at,
        )
        statuses = self._build_budget_statuses(
            db,
            workflow_execution_id=workflow_execution_id,
            project_id=project_id,
            user_id=user_id,
            node_execution_id=node_execution_id,
            budget_config=budget_config,
            recorded_at=recorded_at,
        )
        return BudgetCheckResultDTO(
            usage=usage,
            statuses=statuses,
            exceeded_status=next((status for status in statuses if status.exceeded), None),
        )

    def _create_token_usage(
        self,
        db: Session,
        *,
        project_id: uuid.UUID,
        node_execution_id: uuid.UUID | None,
        credential_id: uuid.UUID,
        usage_type: UsageType,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        recorded_at: datetime,
    ) -> TokenUsageRecordDTO:
        estimated_cost = self.model_pricing.calculate_cost(model_name, input_tokens, output_tokens)
        usage = TokenUsage(
            project_id=project_id,
            node_execution_id=node_execution_id,
            credential_id=credential_id,
            usage_type=usage_type,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=estimated_cost,
            created_at=recorded_at,
        )
        db.add(usage)
        db.flush()
        return TokenUsageRecordDTO(
            token_usage_id=usage.id,
            project_id=project_id,
            node_execution_id=node_execution_id,
            credential_id=credential_id,
            usage_type=usage_type,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            estimated_cost=estimated_cost,
        )

    def _build_budget_statuses(
        self,
        db: Session,
        *,
        workflow_execution_id: uuid.UUID,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        node_execution_id: uuid.UUID | None,
        budget_config: BudgetConfig,
        recorded_at: datetime,
    ) -> tuple[BudgetStatusDTO, ...]:
        self._validate_budget_config(budget_config)
        start_at, end_at = self._day_window(recorded_at)
        statuses = [
            self._build_budget_status(
                scope="node",
                used_tokens=self._sum_node_tokens(db, node_execution_id),
                limit_tokens=budget_config.max_tokens_per_node,
                warning_threshold=budget_config.warning_threshold,
            ),
            self._build_budget_status(
                scope="workflow",
                used_tokens=self._sum_workflow_tokens(db, workflow_execution_id),
                limit_tokens=budget_config.max_tokens_per_workflow,
                warning_threshold=budget_config.warning_threshold,
            ),
            self._build_budget_status(
                scope="project_day",
                used_tokens=self._sum_project_daily_tokens(db, project_id, start_at, end_at),
                limit_tokens=budget_config.max_tokens_per_day,
                warning_threshold=budget_config.warning_threshold,
            ),
        ]
        if budget_config.max_tokens_per_day_per_user is not None:
            statuses.append(
                self._build_budget_status(
                    scope="user_day",
                    used_tokens=self._sum_user_daily_tokens(db, user_id, start_at, end_at),
                    limit_tokens=budget_config.max_tokens_per_day_per_user,
                    warning_threshold=budget_config.warning_threshold,
                )
            )
        return tuple(statuses)

    def _build_budget_status(
        self,
        *,
        scope,
        used_tokens: int,
        limit_tokens: int,
        warning_threshold: float,
    ) -> BudgetStatusDTO:
        warning_limit = max(1, ceil(limit_tokens * warning_threshold))
        return BudgetStatusDTO(
            scope=scope,
            used_tokens=used_tokens,
            limit_tokens=limit_tokens,
            warning_threshold=warning_threshold,
            warning_reached=used_tokens >= warning_limit,
            exceeded=used_tokens > limit_tokens,
        )

    def _sum_node_tokens(self, db: Session, node_execution_id: uuid.UUID | None) -> int:
        if node_execution_id is None:
            return ZERO_TOKENS
        query = db.query(TokenUsage).filter(TokenUsage.node_execution_id == node_execution_id)
        return self._sum_tokens(query)

    def _sum_workflow_tokens(self, db: Session, workflow_execution_id: uuid.UUID) -> int:
        query = (
            db.query(TokenUsage)
            .join(NodeExecution, TokenUsage.node_execution_id == NodeExecution.id)
            .filter(NodeExecution.workflow_execution_id == workflow_execution_id)
        )
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
        user_id: uuid.UUID,
        start_at: datetime,
        end_at: datetime,
    ) -> int:
        query = (
            db.query(TokenUsage)
            .join(Project, TokenUsage.project_id == Project.id)
            .filter(Project.owner_id == user_id)
            .filter(TokenUsage.created_at >= start_at, TokenUsage.created_at < end_at)
        )
        return self._sum_tokens(query)

    def _sum_tokens(self, query: Query[TokenUsage]) -> int:
        total = query.with_entities(
            func.coalesce(func.sum(TokenUsage.input_tokens + TokenUsage.output_tokens), ZERO_TOKENS)
        ).scalar()
        return int(total or ZERO_TOKENS)

    def _normalize_usage_tokens(
        self,
        *,
        usage_type: str,
        model_name: str,
        input_tokens: int | None,
        output_tokens: int | None,
    ) -> tuple[int, int]:
        if usage_type not in SUPPORTED_USAGE_TYPES:
            raise ConfigurationError(f"Unsupported usage_type: {usage_type}")
        if not model_name.strip():
            raise ConfigurationError("model_name must be a non-empty string")
        if input_tokens is None or output_tokens is None:
            raise ConfigurationError(
                f"LLM response is missing token usage for billing: usage_type={usage_type}"
            )
        if input_tokens < ZERO_TOKENS or output_tokens < ZERO_TOKENS:
            raise ConfigurationError("LLM token usage must be >= 0")
        return input_tokens, output_tokens

    def _validate_budget_config(self, budget_config: BudgetConfig) -> None:
        self._ensure_positive_limit("max_tokens_per_node", budget_config.max_tokens_per_node)
        self._ensure_positive_limit("max_tokens_per_workflow", budget_config.max_tokens_per_workflow)
        self._ensure_positive_limit("max_tokens_per_day", budget_config.max_tokens_per_day)
        user_limit = budget_config.max_tokens_per_day_per_user
        if user_limit is not None:
            self._ensure_positive_limit("max_tokens_per_day_per_user", user_limit)
        threshold = budget_config.warning_threshold
        if threshold <= 0 or threshold > 1:
            raise ConfigurationError("warning_threshold must be within (0, 1]")

    def _ensure_positive_limit(self, field_name: str, value: int) -> None:
        if value < 1:
            raise ConfigurationError(f"{field_name} must be >= 1")

    def _day_window(self, recorded_at: datetime) -> tuple[datetime, datetime]:
        day_start = recorded_at.astimezone(timezone.utc).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        return day_start, day_start + timedelta(days=1)

    def _utc_now(self) -> datetime:
        return datetime.now(timezone.utc)
