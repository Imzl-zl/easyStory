from __future__ import annotations

from datetime import UTC, datetime

from app.main import create_app
from app.modules.review.models import ReviewAction
from app.modules.workflow.models import NodeExecution
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers as _auth_headers
from tests.unit.models.helpers import create_project, create_user, create_workflow


async def test_review_summary_api_supports_filters(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="review-summary-api-filters")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
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
                created_at=datetime(2026, 3, 22, 11, 0, tzinfo=UTC),
            )
            _create_review_action(
                session,
                chapter_execution.id,
                review_type="auto_re_review_1",
                status="passed",
                issues=[],
                created_at=datetime(2026, 3, 22, 11, 1, tzinfo=UTC),
            )
            workflow_id = workflow.id
            owner_id = owner.id
            node_execution_id = chapter_execution.id

        async with started_async_client(app) as client:
            response = await client.get(
                f"/api/v1/workflows/{workflow_id}/reviews/summary",
                params={
                    "node_execution_id": str(node_execution_id),
                    "review_type": "auto_review",
                    "status": "failed",
                },
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 200
        summary = response.json()
        assert summary["reviewed_node_count"] == 1
        assert summary["total_actions"] == 1
        assert summary["statuses"] == {"passed": 0, "failed": 1, "warning": 0}
        assert summary["review_types"] == [
            {
                "review_type": "auto_review",
                "action_count": 1,
                "statuses": {"passed": 0, "failed": 1, "warning": 0},
                "issues": {
                    "total": 1,
                    "critical": 1,
                    "major": 0,
                    "minor": 0,
                    "suggestion": 0,
                },
            }
        ]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_review_summary_api_rejects_foreign_node_execution(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="review-summary-api-foreign-node")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
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
            workflow_id = workflow.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            response = await client.get(
                f"/api/v1/workflows/{workflow_id}/reviews/summary",
                params={"node_execution_id": str(foreign_execution.id)},
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def _create_node_execution(
    db,
    workflow_id,
    *,
    node_id: str,
    node_type: str = "generate",
    node_order: int,
) -> NodeExecution:
    execution = NodeExecution(
        workflow_execution_id=workflow_id,
        node_id=node_id,
        node_type=node_type,
        status="completed",
        sequence=0,
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
