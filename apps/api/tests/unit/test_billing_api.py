from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
import uuid

from app.modules.billing.models import TokenUsage
from app.modules.credential.models import ModelCredential
from app.modules.workflow.models import NodeExecution
from tests.unit.models.helpers import create_project, create_user, create_workflow
from tests.unit.test_workflow_api import (
    _auth_headers,
    _build_runtime_client,
    _build_session_factory,
)

TEST_JWT_SECRET = "test-jwt-secret"
WORKFLOW_BUDGET = {
    "max_tokens_per_node": 500,
    "max_tokens_per_workflow": 500,
    "max_tokens_per_day": 400,
    "max_tokens_per_day_per_user": 400,
    "warning_threshold": 0.8,
    "on_exceed": "pause",
}


def test_billing_api_returns_workflow_summary_and_token_usages(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    client = _build_runtime_client(session_factory)

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            workflow = create_workflow(
                session,
                project=project,
                status="running",
                workflow_snapshot={"budget": WORKFLOW_BUDGET},
            )
            credential = _create_credential(session, owner.id)
            chapter_gen_execution = _create_node_execution(
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
            _create_token_usage(
                session,
                project_id=project.id,
                node_execution_id=chapter_gen_execution.id,
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
                node_execution_id=review_execution.id,
                credential_id=credential.id,
                usage_type="review",
                input_tokens=30,
                output_tokens=20,
                estimated_cost=Decimal("0.005000"),
                created_at=datetime(2026, 3, 21, 12, 1, tzinfo=UTC),
            )
            workflow_id = workflow.id
            owner_id = owner.id

        headers = _auth_headers(owner_id)
        summary_response = client.get(
            f"/api/v1/workflows/{workflow_id}/billing/summary",
            headers=headers,
        )
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["workflow_execution_id"] == str(workflow_id)
        assert summary["total_tokens"] == 200
        assert summary["on_exceed"] == "pause"
        assert [item["usage_type"] for item in summary["usage_by_type"]] == ["generate", "review"]
        assert {item["scope"]: item["used_tokens"] for item in summary["budget_statuses"]} == {
            "workflow": 200,
            "project_day": 200,
            "user_day": 200,
        }

        usages_response = client.get(
            f"/api/v1/workflows/{workflow_id}/billing/token-usages",
            params={"usage_type": "review", "limit": 1},
            headers=headers,
        )
        assert usages_response.status_code == 200
        usages = usages_response.json()
        assert len(usages) == 1
        assert usages[0]["usage_type"] == "review"
        assert usages[0]["total_tokens"] == 50
    finally:
        client.close()
        engine.dispose()


def test_billing_api_hides_other_users_workflow(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    client = _build_runtime_client(session_factory)

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            workflow = create_workflow(
                session,
                project=project,
                status="running",
                workflow_snapshot={"budget": WORKFLOW_BUDGET},
            )
            outsider = create_user(session)
            workflow_id = workflow.id
            outsider_id = outsider.id

        response = client.get(
            f"/api/v1/workflows/{workflow_id}/billing/summary",
            headers=_auth_headers(outsider_id),
        )
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
    finally:
        client.close()
        engine.dispose()


def _create_credential(db, owner_id: uuid.UUID) -> ModelCredential:
    credential = ModelCredential(
        owner_type="user",
        owner_id=owner_id,
        provider="openai",
        display_name="openai-test",
        encrypted_key="test-key",
        is_active=True,
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return credential


def _create_node_execution(
    db,
    workflow_id: uuid.UUID,
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


def _create_token_usage(
    db,
    *,
    project_id: uuid.UUID,
    node_execution_id: uuid.UUID,
    credential_id: uuid.UUID,
    usage_type: str,
    input_tokens: int,
    output_tokens: int,
    estimated_cost: Decimal,
    created_at: datetime,
) -> TokenUsage:
    usage = TokenUsage(
        project_id=project_id,
        node_execution_id=node_execution_id,
        credential_id=credential_id,
        usage_type=usage_type,
        model_name="gpt-4o",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost=estimated_cost,
        created_at=created_at,
    )
    db.add(usage)
    db.commit()
    db.refresh(usage)
    return usage
