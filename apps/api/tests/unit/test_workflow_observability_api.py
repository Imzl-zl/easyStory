from __future__ import annotations

import uuid

from app.modules.workflow.models import NodeExecution
from tests.unit.models.helpers import create_user
from tests.unit.test_workflow_api import (
    _auth_headers,
    _build_runtime_client,
    _build_session_factory,
    _seed_project,
)

TEST_JWT_SECRET = "test-jwt-secret"


def test_workflow_observability_api_lists_executions_logs_and_prompt_replays(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    client = _build_runtime_client(session_factory)
    headers = _auth_headers(owner_id)

    try:
        start_response = client.post(
            f"/api/v1/projects/{project_id}/workflows/start",
            headers=headers,
        )
        execution_id = start_response.json()["execution_id"]

        resume_response = client.post(
            f"/api/v1/workflows/{execution_id}/resume",
            headers=headers,
        )
        assert resume_response.status_code == 200

        executions_response = client.get(
            f"/api/v1/workflows/{execution_id}/executions",
            headers=headers,
        )
        assert executions_response.status_code == 200
        executions = executions_response.json()
        assert [item["node_id"] for item in executions] == ["chapter_split", "chapter_gen"]
        assert executions[1]["context_report"]["sections"]
        assert executions[1]["review_actions"][0]["review_type"] == "auto_review"

        logs_response = client.get(
            f"/api/v1/workflows/{execution_id}/logs",
            params={"level": "INFO", "limit": 20},
            headers=headers,
        )
        assert logs_response.status_code == 200
        messages = [item["message"] for item in logs_response.json()]
        assert "Workflow started" in messages
        assert "Node completed" in messages

        with session_factory() as session:
            chapter_gen = (
                session.query(NodeExecution)
                .filter(
                    NodeExecution.workflow_execution_id == uuid.UUID(execution_id),
                    NodeExecution.node_id == "chapter_gen",
                )
                .one()
            )
            chapter_gen_id = chapter_gen.id

        replays_response = client.get(
            f"/api/v1/workflows/{execution_id}/node-executions/{chapter_gen_id}/prompt-replays",
            headers=headers,
        )
        assert replays_response.status_code == 200
        replays = replays_response.json()
        assert [item["replay_type"] for item in replays] == ["generate"]
        assert "林渊" in replays[0]["response_text"]
    finally:
        client.close()
        engine.dispose()


def test_workflow_observability_api_hides_other_users_workflow(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    client = _build_runtime_client(session_factory)
    owner_headers = _auth_headers(owner_id)

    try:
        start_response = client.post(
            f"/api/v1/projects/{project_id}/workflows/start",
            headers=owner_headers,
        )
        execution_id = start_response.json()["execution_id"]
        with session_factory() as session:
            outsider_headers = _auth_headers(create_user(session).id)

        response = client.get(
            f"/api/v1/workflows/{execution_id}/logs",
            headers=outsider_headers,
        )
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
    finally:
        client.close()
        engine.dispose()
