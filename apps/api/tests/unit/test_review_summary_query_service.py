from __future__ import annotations

from datetime import datetime

import pytest

from app.modules.review.models import ReviewAction
from app.modules.review.service import create_review_query_service
from app.modules.workflow.models import NodeExecution
from app.shared.runtime.errors import NotFoundError
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
)
from tests.unit.models.helpers import create_project, create_user, create_workflow


async def test_review_query_service_filters_workflow_summary(tmp_path) -> None:
    service = create_review_query_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="review-summary-query-service")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            workflow = create_workflow(session, project=project, status="paused")
            chapter_execution = _create_node_execution(
                session,
                workflow.id,
                node_id="chapter_gen",
                node_order=1,
            )
            review_execution = _create_node_execution(
                session,
                workflow.id,
                node_id="review",
                node_type="review",
                node_order=2,
            )
            _create_review_action(
                session,
                chapter_execution.id,
                review_type="auto_review",
                status="failed",
                issues=[
                    {
                        "category": "logic_error",
                        "severity": "critical",
                        "description": "剧情冲突",
                    }
                ],
                created_at=datetime(2026, 3, 22, 10, 0),
            )
            _create_review_action(
                session,
                chapter_execution.id,
                review_type="auto_re_review_1",
                status="passed",
                issues=[],
                created_at=datetime(2026, 3, 22, 10, 1),
            )
            _create_review_action(
                session,
                review_execution.id,
                review_type="manual_review",
                status="warning",
                issues=[
                    {
                        "category": "other",
                        "severity": "suggestion",
                        "description": "建议压缩一句",
                    }
                ],
                created_at=datetime(2026, 3, 22, 10, 2),
            )
            owner_id = owner.id
            workflow_id = workflow.id
            chapter_execution_id = chapter_execution.id

        async with async_session_factory() as session:
            summary = await service.get_workflow_summary(
                session,
                workflow_id,
                owner_id=owner_id,
                node_execution_id=chapter_execution_id,
                review_type="auto_review",
                status="failed",
            )

        assert summary.reviewed_node_count == 1
        assert summary.total_actions == 1
        assert summary.last_reviewed_at == datetime(2026, 3, 22, 10, 0)
        assert summary.statuses.model_dump() == {"passed": 0, "failed": 1, "warning": 0}
        assert summary.issues.model_dump() == {
            "total": 1,
            "critical": 1,
            "major": 0,
            "minor": 0,
            "suggestion": 0,
        }
        assert [item.review_type for item in summary.review_types] == ["auto_review"]
        assert summary.review_types[0].action_count == 1
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_review_query_service_rejects_foreign_node_execution_for_summary(tmp_path) -> None:
    service = create_review_query_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="review-summary-query-foreign-node")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            other_project = create_project(session, owner=owner)
            workflow = create_workflow(session, project=project, status="paused")
            other_workflow = create_workflow(session, project=other_project, status="paused")
            foreign_execution = _create_node_execution(
                session,
                other_workflow.id,
                node_id="chapter_gen",
                node_order=1,
            )
            owner_id = owner.id
            workflow_id = workflow.id

        async with async_session_factory() as session:
            with pytest.raises(NotFoundError):
                await service.get_workflow_summary(
                    session,
                    workflow_id,
                    owner_id=owner_id,
                    node_execution_id=foreign_execution.id,
                )
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


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
    review_type: str,
    status: str,
    issues,
    created_at: datetime,
) -> ReviewAction:
    action = ReviewAction(
        node_execution_id=node_execution_id,
        agent_id="agent.style_checker",
        reviewer_name="文风检查员",
        review_type=review_type,
        status=status,
        score=90,
        summary=f"{review_type}-{status}",
        issues=issues,
        execution_time_ms=3,
        tokens_used=12,
        created_at=created_at,
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action
