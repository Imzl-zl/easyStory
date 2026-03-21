from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
import uuid

import pytest

from app.modules.billing.models import TokenUsage
from app.modules.billing.service import BillingQueryService
from app.modules.credential.models import ModelCredential
from app.modules.workflow.models import NodeExecution
from app.shared.runtime.errors import NotFoundError
from tests.unit.models.helpers import create_project, create_user, create_workflow

FIXED_NOW = datetime(2026, 3, 21, 12, 0, tzinfo=UTC)
WORKFLOW_BUDGET = {
    "max_tokens_per_node": 500,
    "max_tokens_per_workflow": 500,
    "max_tokens_per_day": 400,
    "max_tokens_per_day_per_user": 240,
    "warning_threshold": 0.8,
    "on_exceed": "pause",
}


def test_billing_query_service_returns_workflow_summary_and_filtered_usages(db) -> None:
    owner = create_user(db)
    project = create_project(db, owner=owner)
    workflow = create_workflow(
        db,
        project=project,
        status="running",
        workflow_snapshot={"budget": WORKFLOW_BUDGET},
    )
    other_project = create_project(db, owner=owner)
    other_workflow = create_workflow(
        db,
        project=other_project,
        status="running",
        workflow_snapshot={"budget": WORKFLOW_BUDGET},
    )
    credential = _create_credential(db, owner.id)
    chapter_gen_execution = _create_node_execution(db, workflow.id, node_id="chapter_gen", node_order=1)
    review_execution = _create_node_execution(db, workflow.id, node_id="review", node_type="review", node_order=2)
    other_execution = _create_node_execution(db, other_workflow.id, node_id="chapter_gen", node_order=1)
    _create_token_usage(
        db,
        project_id=project.id,
        node_execution_id=chapter_gen_execution.id,
        credential_id=credential.id,
        usage_type="generate",
        input_tokens=100,
        output_tokens=50,
        estimated_cost=Decimal("0.015000"),
        created_at=FIXED_NOW,
    )
    _create_token_usage(
        db,
        project_id=project.id,
        node_execution_id=review_execution.id,
        credential_id=credential.id,
        usage_type="review",
        input_tokens=30,
        output_tokens=20,
        estimated_cost=Decimal("0.005000"),
        created_at=FIXED_NOW,
    )
    _create_token_usage(
        db,
        project_id=other_project.id,
        node_execution_id=other_execution.id,
        credential_id=credential.id,
        usage_type="generate",
        input_tokens=25,
        output_tokens=25,
        estimated_cost=Decimal("0.004000"),
        created_at=FIXED_NOW,
    )

    service = BillingQueryService(now_factory=lambda: FIXED_NOW)

    summary = service.get_workflow_summary(db, workflow.id, owner_id=owner.id)
    usages = service.list_workflow_token_usages(
        db,
        workflow.id,
        owner_id=owner.id,
        usage_type="review",
        limit=10,
    )

    assert summary.total_input_tokens == 130
    assert summary.total_output_tokens == 70
    assert summary.total_tokens == 200
    assert summary.total_estimated_cost == Decimal("0.020000")
    assert [item.usage_type for item in summary.usage_by_type] == ["generate", "review"]
    assert summary.usage_by_type[0].call_count == 1
    assert summary.usage_by_type[0].total_tokens == 150
    assert summary.usage_by_type[1].estimated_cost == Decimal("0.005000")
    assert {item.scope: item.used_tokens for item in summary.budget_statuses} == {
        "workflow": 200,
        "project_day": 200,
        "user_day": 250,
    }
    user_day_status = next(item for item in summary.budget_statuses if item.scope == "user_day")
    assert user_day_status.exceeded is True
    assert len(usages) == 1
    assert usages[0].usage_type == "review"
    assert usages[0].total_tokens == 50


def test_billing_query_service_hides_other_users_workflow(db) -> None:
    owner = create_user(db)
    outsider = create_user(db)
    project = create_project(db, owner=owner)
    workflow = create_workflow(
        db,
        project=project,
        status="running",
        workflow_snapshot={"budget": WORKFLOW_BUDGET},
    )

    service = BillingQueryService(now_factory=lambda: FIXED_NOW)

    with pytest.raises(NotFoundError):
        service.get_workflow_summary(db, workflow.id, owner_id=outsider.id)
    with pytest.raises(NotFoundError):
        service.list_workflow_token_usages(db, workflow.id, owner_id=outsider.id)


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
