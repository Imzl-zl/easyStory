from __future__ import annotations

from decimal import Decimal
import uuid
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.project.models import Project
from app.modules.review.engine.contracts import ReviewIssue
from app.modules.review.models import ReviewAction
from app.modules.workflow.models import NodeExecution, WorkflowExecution
from app.shared.runtime.errors import ConfigurationError, NotFoundError

from .dto import (
    ReviewStatus,
    WorkflowReviewActionDTO,
    WorkflowReviewSummaryDTO,
)
from .review_query_support import (
    build_review_action_records_statement,
    build_review_actions_statement,
    build_reviewed_node_count_statement,
    build_review_type_summaries,
    last_reviewed_at,
    ReviewAggregate,
)


class ReviewQueryService:
    async def get_workflow_summary(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        node_execution_id: uuid.UUID | None = None,
        review_type: str | None = None,
        status: ReviewStatus | None = None,
    ) -> WorkflowReviewSummaryDTO:
        workflow = await self._require_review_scope(
            db,
            workflow_id,
            owner_id=owner_id,
            node_execution_id=node_execution_id,
        )
        actions = await self._list_workflow_actions(
            db,
            workflow.id,
            node_execution_id=node_execution_id,
            review_type=review_type,
            status=status,
        )
        aggregate = ReviewAggregate()
        grouped: dict[str, ReviewAggregate] = {}
        for action in actions:
            issues = self._parse_issues(action)
            aggregate.add(action, issues)
            grouped.setdefault(action.review_type, ReviewAggregate()).add(action, issues)
        return WorkflowReviewSummaryDTO(
            workflow_execution_id=workflow.id,
            project_id=workflow.project_id,
            workflow_status=workflow.status,
            reviewed_node_count=await self._count_reviewed_nodes(
                db,
                workflow.id,
                node_execution_id=node_execution_id,
                review_type=review_type,
                status=status,
            ),
            total_actions=len(actions),
            last_reviewed_at=last_reviewed_at(actions),
            statuses=aggregate.to_status_summary(),
            issues=aggregate.to_issue_summary(),
            review_types=build_review_type_summaries(grouped, actions),
        )

    async def list_workflow_review_actions(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        node_execution_id: uuid.UUID | None = None,
        review_type: str | None = None,
        status: ReviewStatus | None = None,
        limit: int = 100,
    ) -> list[WorkflowReviewActionDTO]:
        await self._require_review_scope(
            db,
            workflow_id,
            owner_id=owner_id,
            node_execution_id=node_execution_id,
        )
        statement = build_review_action_records_statement(
            workflow_id,
            node_execution_id=node_execution_id,
            review_type=review_type,
            status=status,
        )
        statement = statement.order_by(ReviewAction.created_at.desc(), ReviewAction.id.desc()).limit(limit)
        records = (await db.execute(statement)).all()
        return [self._to_action_view(action, execution) for action, execution in records]

    async def _list_workflow_actions(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        node_execution_id: uuid.UUID | None = None,
        review_type: str | None = None,
        status: ReviewStatus | None = None,
    ) -> list[ReviewAction]:
        statement = (
            build_review_actions_statement(
                workflow_id,
                node_execution_id=node_execution_id,
                review_type=review_type,
                status=status,
            )
            .order_by(ReviewAction.created_at.asc(), ReviewAction.id.asc())
        )
        return (await db.scalars(statement)).all()

    async def _count_reviewed_nodes(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        node_execution_id: uuid.UUID | None = None,
        review_type: str | None = None,
        status: ReviewStatus | None = None,
    ) -> int:
        total = await db.scalar(
            build_reviewed_node_count_statement(
                workflow_id,
                node_execution_id=node_execution_id,
                review_type=review_type,
                status=status,
            )
        )
        return int(total or 0)

    async def _require_review_scope(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        node_execution_id: uuid.UUID | None,
    ) -> WorkflowExecution:
        if node_execution_id is None:
            return await self._require_owned_workflow(db, workflow_id, owner_id=owner_id)
        await self._require_owned_node_execution(
            db,
            workflow_id,
            node_execution_id,
            owner_id=owner_id,
        )
        return await self._require_owned_workflow(db, workflow_id, owner_id=owner_id)

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

    async def _require_owned_node_execution(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        node_execution_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> NodeExecution:
        execution = await db.scalar(
            select(NodeExecution)
            .join(WorkflowExecution, NodeExecution.workflow_execution_id == WorkflowExecution.id)
            .join(Project, WorkflowExecution.project_id == Project.id)
            .where(
                NodeExecution.id == node_execution_id,
                WorkflowExecution.id == workflow_id,
                Project.owner_id == owner_id,
            )
        )
        if execution is None:
            raise NotFoundError(f"Node execution not found: {node_execution_id}")
        return execution

    def _to_action_view(
        self,
        action: ReviewAction,
        execution: NodeExecution,
    ) -> WorkflowReviewActionDTO:
        issues = self._parse_issues(action)
        score = float(action.score) if isinstance(action.score, Decimal) else action.score
        return WorkflowReviewActionDTO(
            id=action.id,
            node_execution_id=execution.id,
            node_id=execution.node_id,
            node_type=execution.node_type,
            node_order=execution.node_order,
            sequence=execution.sequence,
            agent_id=action.agent_id,
            reviewer_name=action.reviewer_name,
            review_type=action.review_type,
            status=action.status,
            score=score,
            summary=action.summary,
            issue_count=len(issues),
            issues=issues,
            execution_time_ms=action.execution_time_ms,
            tokens_used=action.tokens_used,
            created_at=action.created_at,
        )

    def _parse_issues(
        self,
        action: ReviewAction,
    ) -> list[ReviewIssue]:
        raw_issues: Any = action.issues
        if raw_issues is None:
            return []
        try:
            if isinstance(raw_issues, list):
                return [ReviewIssue.model_validate(item) for item in raw_issues]
            if isinstance(raw_issues, dict) and isinstance(raw_issues.get("items"), list):
                return [ReviewIssue.model_validate(item) for item in raw_issues["items"]]
        except ValidationError as exc:
            raise ConfigurationError(
                f"Malformed review issues payload for review action {action.id}"
            ) from exc
        raise ConfigurationError(
            f"Malformed review issues payload for review action {action.id}"
        )
