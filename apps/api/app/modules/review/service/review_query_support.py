from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import uuid

from sqlalchemy import func, select

from app.modules.review.engine.contracts import ReviewIssue
from app.modules.review.models import ReviewAction
from app.modules.workflow.models import NodeExecution

from .dto import (
    ReviewIssueSummaryDTO,
    ReviewStatus,
    ReviewStatusSummaryDTO,
    ReviewTypeSummaryDTO,
)


@dataclass
class ReviewAggregate:
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


def build_review_action_records_statement(
    workflow_id: uuid.UUID,
    *,
    node_execution_id: uuid.UUID | None,
    review_type: str | None,
    status: ReviewStatus | None,
):
    statement = (
        select(ReviewAction, NodeExecution)
        .join(NodeExecution, ReviewAction.node_execution_id == NodeExecution.id)
        .where(NodeExecution.workflow_execution_id == workflow_id)
    )
    return apply_review_filters(
        statement,
        node_execution_id=node_execution_id,
        review_type=review_type,
        status=status,
    )


def build_review_actions_statement(
    workflow_id: uuid.UUID,
    *,
    node_execution_id: uuid.UUID | None,
    review_type: str | None,
    status: ReviewStatus | None,
):
    statement = (
        select(ReviewAction)
        .join(NodeExecution, ReviewAction.node_execution_id == NodeExecution.id)
        .where(NodeExecution.workflow_execution_id == workflow_id)
    )
    return apply_review_filters(
        statement,
        node_execution_id=node_execution_id,
        review_type=review_type,
        status=status,
    )


def build_reviewed_node_count_statement(
    workflow_id: uuid.UUID,
    *,
    node_execution_id: uuid.UUID | None,
    review_type: str | None,
    status: ReviewStatus | None,
):
    statement = (
        select(func.count(func.distinct(NodeExecution.node_id)))
        .select_from(NodeExecution)
        .join(ReviewAction, ReviewAction.node_execution_id == NodeExecution.id)
        .where(NodeExecution.workflow_execution_id == workflow_id)
    )
    return apply_review_filters(
        statement,
        node_execution_id=node_execution_id,
        review_type=review_type,
        status=status,
    )


def apply_review_filters(
    statement,
    *,
    node_execution_id: uuid.UUID | None,
    review_type: str | None,
    status: ReviewStatus | None,
):
    if node_execution_id is not None:
        statement = statement.where(NodeExecution.id == node_execution_id)
    if review_type is not None:
        statement = statement.where(ReviewAction.review_type == review_type)
    if status is not None:
        statement = statement.where(ReviewAction.status == status)
    return statement


def build_review_type_summaries(
    grouped: dict[str, ReviewAggregate],
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


def last_reviewed_at(actions: list[ReviewAction]) -> datetime | None:
    if not actions:
        return None
    return actions[-1].created_at
