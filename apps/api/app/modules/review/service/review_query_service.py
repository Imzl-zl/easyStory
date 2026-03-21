from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import uuid
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.project.models import Project
from app.modules.review.engine.contracts import ReviewIssue
from app.modules.review.models import ReviewAction
from app.modules.workflow.models import NodeExecution, WorkflowExecution
from app.shared.runtime.errors import ConfigurationError, NotFoundError

from .dto import (
    ReviewIssueSummaryDTO,
    ReviewStatus,
    ReviewStatusSummaryDTO,
    ReviewTypeSummaryDTO,
    WorkflowReviewActionDTO,
    WorkflowReviewSummaryDTO,
)


@dataclass
class _ReviewAggregate:
    passed: int = 0
    failed: int = 0
    warning: int = 0
    total: int = 0
    critical: int = 0
    major: int = 0
    minor: int = 0
    suggestion: int = 0

    def add(self, action: ReviewAction, issues: list[ReviewIssue]) -> None:
        if action.status == "passed":
            self.passed += 1
        elif action.status == "failed":
            self.failed += 1
        else:
            self.warning += 1
        self.total += len(issues)
        for issue in issues:
            if issue.severity == "critical":
                self.critical += 1
            elif issue.severity == "major":
                self.major += 1
            elif issue.severity == "minor":
                self.minor += 1
            else:
                self.suggestion += 1

    def to_status_summary(self) -> ReviewStatusSummaryDTO:
        return ReviewStatusSummaryDTO(
            passed=self.passed,
            failed=self.failed,
            warning=self.warning,
        )

    def to_issue_summary(self) -> ReviewIssueSummaryDTO:
        return ReviewIssueSummaryDTO(
            total=self.total,
            critical=self.critical,
            major=self.major,
            minor=self.minor,
            suggestion=self.suggestion,
        )


class ReviewQueryService:
    async def get_workflow_summary(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowReviewSummaryDTO:
        workflow = await self._require_owned_workflow(db, workflow_id, owner_id=owner_id)
        actions = await self._list_workflow_actions(db, workflow.id)
        aggregate = _ReviewAggregate()
        grouped: dict[str, _ReviewAggregate] = {}
        for action in actions:
            issues = self._parse_issues(action)
            aggregate.add(action, issues)
            grouped.setdefault(action.review_type, _ReviewAggregate()).add(action, issues)
        return WorkflowReviewSummaryDTO(
            workflow_execution_id=workflow.id,
            project_id=workflow.project_id,
            workflow_status=workflow.status,
            reviewed_node_count=await self._count_reviewed_nodes(db, workflow.id),
            total_actions=len(actions),
            last_reviewed_at=self._last_reviewed_at(actions),
            statuses=aggregate.to_status_summary(),
            issues=aggregate.to_issue_summary(),
            review_types=self._build_review_type_summaries(grouped, actions),
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
        if node_execution_id is None:
            await self._require_owned_workflow(db, workflow_id, owner_id=owner_id)
        else:
            await self._require_owned_node_execution(
                db,
                workflow_id,
                node_execution_id,
                owner_id=owner_id,
            )
        statement = (
            select(ReviewAction, NodeExecution)
            .join(NodeExecution, ReviewAction.node_execution_id == NodeExecution.id)
            .where(NodeExecution.workflow_execution_id == workflow_id)
        )
        if node_execution_id is not None:
            statement = statement.where(NodeExecution.id == node_execution_id)
        if review_type is not None:
            statement = statement.where(ReviewAction.review_type == review_type)
        if status is not None:
            statement = statement.where(ReviewAction.status == status)
        statement = statement.order_by(ReviewAction.created_at.desc(), ReviewAction.id.desc()).limit(limit)
        records = (await db.execute(statement)).all()
        return [self._to_action_view(action, execution) for action, execution in records]

    async def _list_workflow_actions(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
    ) -> list[ReviewAction]:
        statement = (
            select(ReviewAction)
            .join(NodeExecution, ReviewAction.node_execution_id == NodeExecution.id)
            .where(NodeExecution.workflow_execution_id == workflow_id)
            .order_by(ReviewAction.created_at.asc(), ReviewAction.id.asc())
        )
        return (await db.scalars(statement)).all()

    async def _count_reviewed_nodes(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
    ) -> int:
        total = await db.scalar(
            select(func.count(func.distinct(NodeExecution.node_id)))
            .select_from(NodeExecution)
            .join(ReviewAction, ReviewAction.node_execution_id == NodeExecution.id)
            .where(NodeExecution.workflow_execution_id == workflow_id)
        )
        return int(total or 0)

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

    def _build_review_type_summaries(
        self,
        grouped: dict[str, _ReviewAggregate],
        actions: list[ReviewAction],
    ) -> list[ReviewTypeSummaryDTO]:
        counts: dict[str, int] = {}
        for action in actions:
            counts[action.review_type] = counts.get(action.review_type, 0) + 1
        return [
            ReviewTypeSummaryDTO(
                review_type=review_type,
                action_count=counts.get(review_type, 0),
                statuses=aggregate.to_status_summary(),
                issues=aggregate.to_issue_summary(),
            )
            for review_type, aggregate in sorted(grouped.items(), key=lambda item: item[0])
        ]

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

    def _last_reviewed_at(
        self,
        actions: list[ReviewAction],
    ) -> datetime | None:
        if not actions:
            return None
        return actions[-1].created_at
