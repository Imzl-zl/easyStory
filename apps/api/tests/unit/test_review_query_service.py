from __future__ import annotations

from datetime import datetime

import pytest

from app.modules.review.models import ReviewAction
from app.modules.review.service import ReviewQueryService
from app.modules.workflow.models import NodeExecution
from app.shared.runtime.errors import ConfigurationError, NotFoundError
from tests.unit.models.helpers import create_project, create_user, create_workflow


def test_review_query_service_returns_workflow_summary_and_filtered_actions(db) -> None:
    owner = create_user(db)
    project = create_project(db, owner=owner)
    workflow = create_workflow(db, project=project, status="paused")
    chapter_execution = _create_node_execution(
        db,
        workflow.id,
        node_id="chapter_gen",
        node_order=1,
    )
    review_execution = _create_node_execution(
        db,
        workflow.id,
        node_id="review",
        node_type="review",
        node_order=2,
    )
    chapter_retry_execution = _create_node_execution(
        db,
        workflow.id,
        node_id="chapter_gen",
        node_order=1,
        sequence=1,
    )
    _create_review_action(
        db,
        chapter_execution.id,
        agent_id="agent.style_checker",
        review_type="auto_review",
        status="failed",
        issues=[
            {
                "category": "style_deviation",
                "severity": "major",
                "description": "文风偏移",
            },
            {
                "category": "ai_flavor",
                "severity": "minor",
                "description": "AI 味偏重",
            },
        ],
        created_at=datetime(2026, 3, 21, 12, 0),
    )
    _create_review_action(
        db,
        chapter_execution.id,
        agent_id="agent.style_checker",
        review_type="auto_re_review_1",
        status="passed",
        issues=[],
        created_at=datetime(2026, 3, 21, 12, 1),
    )
    _create_review_action(
        db,
        review_execution.id,
        agent_id="agent.logic_checker",
        review_type="manual_review",
        status="warning",
        issues={
            "items": [
                {
                    "category": "other",
                    "severity": "suggestion",
                    "description": "可以再压缩一句",
                }
            ]
        },
        created_at=datetime(2026, 3, 21, 12, 2),
    )
    _create_review_action(
        db,
        chapter_retry_execution.id,
        agent_id="agent.style_checker",
        review_type="auto_review",
        status="passed",
        issues=[],
        created_at=datetime(2026, 3, 21, 12, 3),
    )

    service = ReviewQueryService()

    summary = service.get_workflow_summary(db, workflow.id, owner_id=owner.id)
    actions = service.list_workflow_review_actions(
        db,
        workflow.id,
        owner_id=owner.id,
        node_execution_id=chapter_execution.id,
        status="failed",
    )

    assert summary.workflow_execution_id == workflow.id
    assert summary.reviewed_node_count == 2
    assert summary.total_actions == 4
    assert summary.last_reviewed_at == datetime(2026, 3, 21, 12, 3)
    assert summary.statuses.model_dump() == {"passed": 2, "failed": 1, "warning": 1}
    assert summary.issues.model_dump() == {
        "total": 3,
        "critical": 0,
        "major": 1,
        "minor": 1,
        "suggestion": 1,
    }
    review_types = {item.review_type: item.action_count for item in summary.review_types}
    assert review_types == {
        "auto_re_review_1": 1,
        "auto_review": 2,
        "manual_review": 1,
    }
    assert len(actions) == 1
    assert actions[0].node_id == "chapter_gen"
    assert actions[0].review_type == "auto_review"
    assert actions[0].issue_count == 2
    assert actions[0].issues[0].severity == "major"


def test_review_query_service_hides_other_users_workflow(db) -> None:
    owner = create_user(db)
    outsider = create_user(db)
    project = create_project(db, owner=owner)
    workflow = create_workflow(db, project=project, status="running")

    service = ReviewQueryService()

    with pytest.raises(NotFoundError):
        service.get_workflow_summary(db, workflow.id, owner_id=outsider.id)


def test_review_query_service_rejects_node_execution_from_other_workflow(db) -> None:
    owner = create_user(db)
    project = create_project(db, owner=owner)
    other_project = create_project(db, owner=owner)
    workflow = create_workflow(db, project=project, status="running")
    other_workflow = create_workflow(db, project=other_project, status="paused")
    foreign_execution = _create_node_execution(
        db,
        other_workflow.id,
        node_id="chapter_gen",
        node_order=1,
    )

    service = ReviewQueryService()

    with pytest.raises(NotFoundError):
        service.list_workflow_review_actions(
            db,
            workflow.id,
            owner_id=owner.id,
            node_execution_id=foreign_execution.id,
        )


def test_review_query_service_raises_configuration_error_for_malformed_issues(db) -> None:
    owner = create_user(db)
    project = create_project(db, owner=owner)
    workflow = create_workflow(db, project=project, status="paused")
    execution = _create_node_execution(
        db,
        workflow.id,
        node_id="chapter_gen",
        node_order=1,
    )
    action = _create_review_action(
        db,
        execution.id,
        agent_id="agent.style_checker",
        review_type="auto_review",
        status="failed",
        issues="bad-payload",
        created_at=datetime(2026, 3, 21, 14, 0),
    )

    service = ReviewQueryService()

    with pytest.raises(ConfigurationError, match=str(action.id)):
        service.get_workflow_summary(db, workflow.id, owner_id=owner.id)


def _create_node_execution(
    db,
    workflow_id,
    *,
    node_id: str,
    node_type: str = "generate",
    node_order: int,
    sequence: int = 0,
) -> NodeExecution:
    execution = NodeExecution(
        workflow_execution_id=workflow_id,
        node_id=node_id,
        node_type=node_type,
        status="completed",
        sequence=sequence,
        node_order=node_order,
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


def _create_review_action(
    db,
    node_execution_id,
    *,
    agent_id: str,
    review_type: str,
    status: str,
    issues,
    created_at: datetime,
) -> ReviewAction:
    action = ReviewAction(
        node_execution_id=node_execution_id,
        agent_id=agent_id,
        reviewer_name=agent_id,
        review_type=review_type,
        status=status,
        score=95,
        summary=f"{review_type}-{status}",
        issues=issues,
        execution_time_ms=12,
        tokens_used=34,
        created_at=created_at,
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action
