from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.models import TokenUsage
from app.modules.billing.service.dto import BudgetStatusDTO, TokenUsageRecordDTO, UsageType
from app.modules.config_registry.schemas.config_schemas import BudgetConfig
from app.modules.project.models import Project
from app.modules.workflow.models import NodeExecution
from app.shared.runtime import ModelPricing
from app.shared.runtime.errors import ConfigurationError

from .billing_query_support import ZERO_TOKENS, build_budget_status, day_window

SUPPORTED_USAGE_TYPES = frozenset({"generate", "review", "fix", "analysis", "dry_run"})


async def create_token_usage(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    node_execution_id: uuid.UUID | None,
    credential_id: uuid.UUID,
    usage_type: UsageType,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    recorded_at: datetime,
    model_pricing: ModelPricing,
) -> TokenUsageRecordDTO:
    estimated_cost = model_pricing.calculate_cost(model_name, input_tokens, output_tokens)
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
    await db.flush()
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


async def build_budget_statuses(
    db: AsyncSession,
    *,
    workflow_execution_id: uuid.UUID,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    node_execution_id: uuid.UUID | None,
    budget_config: BudgetConfig,
    recorded_at: datetime,
) -> tuple[BudgetStatusDTO, ...]:
    start_at, end_at = day_window(recorded_at)
    statuses = [
        build_budget_status(
            scope="node",
            used_tokens=await sum_node_tokens(db, node_execution_id),
            limit_tokens=budget_config.max_tokens_per_node,
            warning_threshold=budget_config.warning_threshold,
        ),
        build_budget_status(
            scope="workflow",
            used_tokens=await sum_workflow_tokens(db, workflow_execution_id),
            limit_tokens=budget_config.max_tokens_per_workflow,
            warning_threshold=budget_config.warning_threshold,
        ),
        build_budget_status(
            scope="project_day",
            used_tokens=await sum_project_daily_tokens(db, project_id, start_at, end_at),
            limit_tokens=budget_config.max_tokens_per_day,
            warning_threshold=budget_config.warning_threshold,
        ),
    ]
    if budget_config.max_tokens_per_day_per_user is not None:
        statuses.append(
            build_budget_status(
                scope="user_day",
                used_tokens=await sum_user_daily_tokens(db, user_id, start_at, end_at),
                limit_tokens=budget_config.max_tokens_per_day_per_user,
                warning_threshold=budget_config.warning_threshold,
            )
        )
    return tuple(statuses)


async def sum_node_tokens(
    db: AsyncSession,
    node_execution_id: uuid.UUID | None,
) -> int:
    if node_execution_id is None:
        return ZERO_TOKENS
    statement = (
        select(func.coalesce(func.sum(TokenUsage.input_tokens + TokenUsage.output_tokens), ZERO_TOKENS))
        .where(TokenUsage.node_execution_id == node_execution_id)
    )
    return int(await db.scalar(statement) or ZERO_TOKENS)


async def sum_workflow_tokens(
    db: AsyncSession,
    workflow_execution_id: uuid.UUID,
) -> int:
    statement = (
        select(func.coalesce(func.sum(TokenUsage.input_tokens + TokenUsage.output_tokens), ZERO_TOKENS))
        .select_from(TokenUsage)
        .join(NodeExecution, TokenUsage.node_execution_id == NodeExecution.id)
        .where(NodeExecution.workflow_execution_id == workflow_execution_id)
    )
    return int(await db.scalar(statement) or ZERO_TOKENS)


async def sum_project_daily_tokens(
    db: AsyncSession,
    project_id: uuid.UUID,
    start_at: datetime,
    end_at: datetime,
) -> int:
    statement = (
        select(func.coalesce(func.sum(TokenUsage.input_tokens + TokenUsage.output_tokens), ZERO_TOKENS))
        .where(TokenUsage.project_id == project_id)
        .where(TokenUsage.created_at >= start_at, TokenUsage.created_at < end_at)
    )
    return int(await db.scalar(statement) or ZERO_TOKENS)


async def sum_user_daily_tokens(
    db: AsyncSession,
    user_id: uuid.UUID,
    start_at: datetime,
    end_at: datetime,
) -> int:
    statement = (
        select(func.coalesce(func.sum(TokenUsage.input_tokens + TokenUsage.output_tokens), ZERO_TOKENS))
        .select_from(TokenUsage)
        .join(Project, TokenUsage.project_id == Project.id)
        .where(Project.owner_id == user_id)
        .where(TokenUsage.created_at >= start_at, TokenUsage.created_at < end_at)
    )
    return int(await db.scalar(statement) or ZERO_TOKENS)


def normalize_usage_tokens(
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


def validate_budget_config(budget_config: BudgetConfig) -> None:
    ensure_positive_limit("max_tokens_per_node", budget_config.max_tokens_per_node)
    ensure_positive_limit("max_tokens_per_workflow", budget_config.max_tokens_per_workflow)
    ensure_positive_limit("max_tokens_per_day", budget_config.max_tokens_per_day)
    if budget_config.max_tokens_per_day_per_user is not None:
        ensure_positive_limit(
            "max_tokens_per_day_per_user",
            budget_config.max_tokens_per_day_per_user,
        )
    if not 0 < budget_config.warning_threshold <= 1:
        raise ConfigurationError("warning_threshold must be within (0, 1]")


def ensure_positive_limit(field_name: str, value: int) -> None:
    if value <= ZERO_TOKENS:
        raise ConfigurationError(f"{field_name} must be > 0")


__all__ = [
    "build_budget_statuses",
    "create_token_usage",
    "normalize_usage_tokens",
    "validate_budget_config",
]
