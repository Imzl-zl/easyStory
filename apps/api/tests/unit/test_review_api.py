from __future__ import annotations

from datetime import UTC, datetime

from app.modules.review.models import ReviewAction
from app.modules.workflow.models import NodeExecution
from tests.unit.models.helpers import create_project, create_user, create_workflow
from tests.unit.test_workflow_api import (
    TEST_JWT_SECRET,
    _auth_headers,
    _build_runtime_client,
    _build_session_factory,
)


def test_review_api_returns_workflow_summary_and_actions(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    client = _build_runtime_client(session_factory)

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
                created_at=datetime(2026, 3, 21, 13, 0, tzinfo=UTC),
            )
            _create_review_action(
                session,
                chapter_execution.id,
                review_type="auto_re_review_1",
                status="passed",
                issues=[],
                created_at=datetime(2026, 3, 21, 13, 1, tzinfo=UTC),
            )
            workflow_id = workflow.id
            owner_id = owner.id
            node_execution_id = chapter_execution.id

        headers = _auth_headers(owner_id)
        summary_response = client.get(
            f"/api/v1/workflows/{workflow_id}/reviews/summary",
            headers=headers,
        )
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["workflow_execution_id"] == str(workflow_id)
        assert summary["reviewed_node_count"] == 1
        assert summary["statuses"] == {"passed": 1, "failed": 1, "warning": 0}
        assert summary["issues"] == {
            "total": 1,
            "critical": 1,
            "major": 0,
            "minor": 0,
            "suggestion": 0,
        }

        actions_response = client.get(
            f"/api/v1/workflows/{workflow_id}/reviews/actions",
            params={"node_execution_id": str(node_execution_id), "status": "failed"},
            headers=headers,
        )
        assert actions_response.status_code == 200
        actions = actions_response.json()
        assert len(actions) == 1
        assert actions[0]["review_type"] == "auto_review"
        assert actions[0]["node_id"] == "chapter_gen"
        assert actions[0]["issue_count"] == 1
        assert actions[0]["issues"][0]["severity"] == "critical"
    finally:
        client.close()
        engine.dispose()


def test_review_api_hides_other_users_workflow(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    client = _build_runtime_client(session_factory)

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            workflow = create_workflow(session, project=project, status="running")
            outsider = create_user(session)
            workflow_id = workflow.id
            outsider_id = outsider.id

        response = client.get(
            f"/api/v1/workflows/{workflow_id}/reviews/summary",
            headers=_auth_headers(outsider_id),
        )
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
    finally:
        client.close()
        engine.dispose()


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
