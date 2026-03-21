from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.modules.observability.service import ExecutionLogViewDTO
from app.modules.observability.entry.http.router import get_workflow_observability_service
from app.modules.workflow.models import NodeExecution
from tests.unit.models.helpers import create_user
from tests.unit.test_workflow_api import (
    _NoopDispatcher,
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


def test_workflow_events_sse_streams_execution_logs(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    client = _build_runtime_client(
        session_factory,
        runtime_dispatcher=_NoopDispatcher(),
    )
    headers = _auth_headers(owner_id)

    try:
        start_response = client.post(
            f"/api/v1/projects/{project_id}/workflows/start",
            headers=headers,
        )
        execution_id = start_response.json()["execution_id"]

        with client.stream(
            "GET",
            f"/api/v1/workflows/{execution_id}/events",
            params={"timeout_seconds": 1, "poll_interval_ms": 100},
            headers=headers,
        ) as response:
            assert response.status_code == 200
            body = "".join(response.iter_text())

        assert "event: execution_log" in body
        assert "Workflow started" in body
    finally:
        client.close()
        engine.dispose()


def test_workflow_events_sse_uses_composite_cursor(monkeypatch) -> None:
    class _FakeObservabilityService:
        def __init__(self) -> None:
            self.shared_created_at = datetime(2026, 3, 21, 12, 0, tzinfo=UTC)
            self.first = ExecutionLogViewDTO(
                id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                workflow_execution_id=uuid.uuid4(),
                node_execution_id=None,
                level="INFO",
                message="first",
                details=None,
                created_at=self.shared_created_at,
            )
            self.second = ExecutionLogViewDTO(
                id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
                workflow_execution_id=self.first.workflow_execution_id,
                node_execution_id=None,
                level="INFO",
                message="second",
                details=None,
                created_at=self.shared_created_at,
            )
            self.calls: list[tuple[datetime | None, uuid.UUID | None]] = []

        def list_execution_logs_since(
            self,
            db,
            workflow_id,
            *,
            owner_id,
            after_created_at,
            after_id=None,
            level=None,
            limit=100,
        ):
            del db, workflow_id, owner_id, level, limit
            self.calls.append((after_created_at, after_id))
            if len(self.calls) == 1:
                return [self.first]
            if len(self.calls) == 2:
                assert after_created_at == self.shared_created_at
                assert after_id == self.first.id
                return [self.second]
            return []

        def is_workflow_terminal(self, db, workflow_id, *, owner_id):
            del db, workflow_id, owner_id
            return len(self.calls) >= 2

    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    project_id, owner_id = _seed_project(session_factory, ready_assets=True)
    client = _build_runtime_client(
        session_factory,
        runtime_dispatcher=_NoopDispatcher(),
    )
    headers = _auth_headers(owner_id)
    fake_service = _FakeObservabilityService()
    client.app.dependency_overrides[get_workflow_observability_service] = lambda: fake_service

    try:
        start_response = client.post(
            f"/api/v1/projects/{project_id}/workflows/start",
            headers=headers,
        )
        execution_id = start_response.json()["execution_id"]

        with client.stream(
            "GET",
            f"/api/v1/workflows/{execution_id}/events",
            params={"timeout_seconds": 1, "poll_interval_ms": 100},
            headers=headers,
        ) as response:
            assert response.status_code == 200
            body = "".join(response.iter_text())

        assert "message\": \"first\"" in body
        assert "message\": \"second\"" in body
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
