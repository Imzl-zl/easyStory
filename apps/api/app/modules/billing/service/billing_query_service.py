from __future__ import annotations

from datetime import datetime
from typing import Callable
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.models import TokenUsage
from app.modules.billing.service.dto import (
    BudgetStatusViewDTO,
    TokenUsageViewDTO,
    UsageType,
    WorkflowBillingSummaryDTO,
)
from app.modules.config_registry.schemas.config_schemas import BudgetConfig
from app.modules.project.models import Project
from app.modules.workflow.models import NodeExecution, WorkflowExecution
from app.shared.runtime.errors import NotFoundError

from .billing_query_support import (
    ZERO_COST,
    ZERO_TOKENS,
    build_budget_status,
    build_usage_breakdowns,
    day_window,
    load_budget_config,
    normalize_model_name_filter,
    resolve_budget_recorded_at,
    to_budget_status_view,
    to_token_usage_view,
    utc_now,
)


class BillingQueryService:
    def __init__(
        self,
        *,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self.now_factory = now_factory or utc_now

    async def get_workflow_summary(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowBillingSummaryDTO:
        workflow = await self._require_owned_workflow(db, workflow_id, owner_id=owner_id)
        usages = (await db.scalars(self._workflow_usage_statement(workflow.id))).all()
        recorded_at = resolve_budget_recorded_at(usages, self.now_factory)
        budget_window_start_at, budget_window_end_at = day_window(recorded_at)
        usage_by_type = build_usage_breakdowns(usages)
        total_input_tokens = sum(item.input_tokens for item in usage_by_type)
        total_output_tokens = sum(item.output_tokens for item in usage_by_type)
        budget_config = load_budget_config(workflow)
        return WorkflowBillingSummaryDTO(
            workflow_execution_id=workflow.id,
            project_id=workflow.project_id,
            workflow_status=workflow.status,
            on_exceed=budget_config.on_exceed,
            budget_recorded_at=recorded_at,
            budget_window_start_at=budget_window_start_at,
            budget_window_end_at=budget_window_end_at,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_tokens=total_input_tokens + total_output_tokens,
            total_estimated_cost=sum(
                (item.estimated_cost for item in usage_by_type),
                start=ZERO_COST,
            ),
            usage_by_type=usage_by_type,
            budget_statuses=await self._build_budget_status_views(
                db,
                workflow,
                owner_id=owner_id,
                budget_config=budget_config,
                recorded_at=recorded_at,
            ),
        )

    async def list_workflow_token_usages(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        usage_type: UsageType | None = None,
        limit: int = 100,
    ) -> list[TokenUsageViewDTO]:
        workflow = await self._require_owned_workflow(db, workflow_id, owner_id=owner_id)
        statement = self._workflow_usage_statement(workflow.id)
        if usage_type is not None:
            statement = statement.where(TokenUsage.usage_type == usage_type)
        statement = statement.order_by(TokenUsage.created_at.desc(), TokenUsage.id.desc()).limit(limit)
        usages = (await db.scalars(statement)).all()
        return [to_token_usage_view(item, workflow_execution_id=workflow.id) for item in usages]

    async def list_project_token_usages(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        workflow_id: uuid.UUID | None = None,
        usage_type: UsageType | None = None,
        model_name: str | None = None,
        limit: int = 100,
    ) -> list[TokenUsageViewDTO]:
        await self._require_owned_project(db, project_id, owner_id=owner_id)
        scoped_workflow_id = await self._resolve_project_workflow_scope(
            db,
            project_id,
            workflow_id=workflow_id,
            owner_id=owner_id,
        )
        normalized_model_name = normalize_model_name_filter(model_name)
        statement = self._project_usage_statement(project_id)
        if scoped_workflow_id is not None:
            statement = statement.where(NodeExecution.workflow_execution_id == scoped_workflow_id)
        if usage_type is not None:
            statement = statement.where(TokenUsage.usage_type == usage_type)
        if normalized_model_name is not None:
            statement = statement.where(TokenUsage.model_name == normalized_model_name)
        statement = statement.order_by(TokenUsage.created_at.desc(), TokenUsage.id.desc()).limit(limit)
        rows = (await db.execute(statement)).all()
        return [
            to_token_usage_view(usage, workflow_execution_id=workflow_execution_id)
            for usage, workflow_execution_id in rows
        ]

    def _workflow_usage_statement(
        self,
        workflow_id: uuid.UUID,
    ):
        return (
            select(TokenUsage)
            .join(NodeExecution, TokenUsage.node_execution_id == NodeExecution.id)
            .where(NodeExecution.workflow_execution_id == workflow_id)
        )

    def _project_usage_statement(
        self,
        project_id: uuid.UUID,
    ):
        return (
            select(TokenUsage, NodeExecution.workflow_execution_id)
            .select_from(TokenUsage)
            .outerjoin(NodeExecution, TokenUsage.node_execution_id == NodeExecution.id)
            .where(TokenUsage.project_id == project_id)
        )

    async def _build_budget_status_views(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        *,
        owner_id: uuid.UUID,
        budget_config: BudgetConfig,
        recorded_at: datetime,
    ) -> list[BudgetStatusViewDTO]:
        start_at, end_at = day_window(recorded_at)
        statuses = [
            build_budget_status(
                scope="workflow",
                used_tokens=await self._sum_workflow_tokens(db, workflow.id),
                limit_tokens=budget_config.max_tokens_per_workflow,
                warning_threshold=budget_config.warning_threshold,
            ),
            build_budget_status(
                scope="project_day",
                used_tokens=await self._sum_project_daily_tokens(
                    db,
                    workflow.project_id,
                    start_at,
                    end_at,
                ),
                limit_tokens=budget_config.max_tokens_per_day,
                warning_threshold=budget_config.warning_threshold,
            ),
        ]
        if budget_config.max_tokens_per_day_per_user is not None:
            statuses.append(
                build_budget_status(
                    scope="user_day",
                    used_tokens=await self._sum_user_daily_tokens(
                        db,
                        owner_id,
                        start_at,
                        end_at,
                    ),
                    limit_tokens=budget_config.max_tokens_per_day_per_user,
                    warning_threshold=budget_config.warning_threshold,
                )
            )
        return [to_budget_status_view(item) for item in statuses]

    async def _sum_workflow_tokens(self, db: AsyncSession, workflow_id: uuid.UUID) -> int:
        return await self._sum_scalar_tokens(
            db,
            select(func.coalesce(func.sum(TokenUsage.input_tokens + TokenUsage.output_tokens), ZERO_TOKENS))
            .select_from(TokenUsage)
            .join(NodeExecution, TokenUsage.node_execution_id == NodeExecution.id)
            .where(NodeExecution.workflow_execution_id == workflow_id),
        )

    async def _sum_project_daily_tokens(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        start_at: datetime,
        end_at: datetime,
    ) -> int:
        return await self._sum_scalar_tokens(
            db,
            select(func.coalesce(func.sum(TokenUsage.input_tokens + TokenUsage.output_tokens), ZERO_TOKENS))
            .where(
                TokenUsage.project_id == project_id,
                TokenUsage.created_at >= start_at,
                TokenUsage.created_at < end_at,
            ),
        )

    async def _sum_user_daily_tokens(
        self,
        db: AsyncSession,
        owner_id: uuid.UUID,
        start_at: datetime,
        end_at: datetime,
    ) -> int:
        return await self._sum_scalar_tokens(
            db,
            select(func.coalesce(func.sum(TokenUsage.input_tokens + TokenUsage.output_tokens), ZERO_TOKENS))
            .select_from(TokenUsage)
            .join(Project, TokenUsage.project_id == Project.id)
            .where(
                Project.owner_id == owner_id,
                TokenUsage.created_at >= start_at,
                TokenUsage.created_at < end_at,
            ),
        )

    async def _sum_scalar_tokens(self, db: AsyncSession, statement) -> int:
        total = await db.scalar(statement)
        return int(total or ZERO_TOKENS)

    async def _require_owned_workflow(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowExecution:
        workflow = await db.scalar(
            select(WorkflowExecution)
            .join(Project, WorkflowExecution.project_id == Project.id)
            .where(
                WorkflowExecution.id == workflow_id,
                Project.owner_id == owner_id,
            )
        )
        if workflow is None:
            raise NotFoundError(f"Workflow execution not found: {workflow_id}")
        return workflow

    async def _require_owned_project(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> None:
        project_id_result = await db.scalar(
            select(Project.id).where(
                Project.id == project_id,
                Project.owner_id == owner_id,
            )
        )
        if project_id_result is None:
            raise NotFoundError(f"Project not found: {project_id}")

    async def _resolve_project_workflow_scope(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        workflow_id: uuid.UUID | None,
        owner_id: uuid.UUID,
    ) -> uuid.UUID | None:
        if workflow_id is None:
            return None
        workflow = await self._require_owned_workflow(db, workflow_id, owner_id=owner_id)
        if workflow.project_id != project_id:
            raise NotFoundError(f"Workflow execution not found: {workflow_id}")
        return workflow.id
