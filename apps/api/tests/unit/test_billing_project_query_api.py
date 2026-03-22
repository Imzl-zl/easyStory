from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.main import create_app
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers as _auth_headers
from tests.unit.models.helpers import create_project, create_user, create_workflow
from tests.unit.test_billing_api import _create_credential, _create_node_execution, _create_token_usage


async def test_billing_project_usage_api_returns_filtered_history(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="billing-project-query-api")
    )

    try:
        app = create_app(async_session_factory=async_session_factory)
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            first_workflow = create_workflow(session, project=project, status="running")
            second_workflow = create_workflow(session, project=project, status="completed")
            credential = _create_credential(session, owner.id)
            first_execution = _create_node_execution(
                session,
                first_workflow.id,
                node_id="chapter_gen",
                node_order=1,
            )
            second_execution = _create_node_execution(
                session,
                second_workflow.id,
                node_id="review",
                node_type="review",
                node_order=2,
            )
            _create_token_usage(
                session,
                project_id=project.id,
                node_execution_id=first_execution.id,
                credential_id=credential.id,
                usage_type="generate",
                input_tokens=100,
                output_tokens=50,
                estimated_cost=Decimal("0.015000"),
                created_at=datetime(2026, 3, 21, 12, 0, tzinfo=UTC),
            )
            _create_token_usage(
                session,
                project_id=project.id,
                node_execution_id=second_execution.id,
                credential_id=credential.id,
                usage_type="review",
                input_tokens=30,
                output_tokens=20,
                estimated_cost=Decimal("0.005000"),
                created_at=datetime(2026, 3, 21, 12, 1, tzinfo=UTC),
            )
            project_id = project.id
            workflow_id = second_workflow.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            response = await client.get(
                f"/api/v1/projects/{project_id}/billing/token-usages",
                params={
                    "workflow_id": str(workflow_id),
                    "usage_type": "review",
                    "model_name": "gpt-4o",
                },
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["workflow_execution_id"] == str(workflow_id)
        assert payload[0]["usage_type"] == "review"
        assert payload[0]["total_tokens"] == 50
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_billing_project_usage_api_hides_other_users_project(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="billing-project-query-api-owner")
    )

    try:
        app = create_app(async_session_factory=async_session_factory)
        with session_factory() as session:
            owner = create_user(session)
            outsider = create_user(session)
            project = create_project(session, owner=owner)
            project_id = project.id
            outsider_id = outsider.id

        async with started_async_client(app) as client:
            response = await client.get(
                f"/api/v1/projects/{project_id}/billing/token-usages",
                headers=_auth_headers(outsider_id),
            )

        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
