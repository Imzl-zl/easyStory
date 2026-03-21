from __future__ import annotations

import asyncio
import uuid

import pytest

from app.modules.billing.models import TokenUsage
from app.modules.billing.service import create_billing_service
from app.modules.config_registry.schemas.config_schemas import BudgetConfig
from app.modules.credential.models import ModelCredential
from app.modules.workflow.models import NodeExecution
from app.shared.runtime.errors import ConfigurationError
from tests.unit.async_service_support import async_db
from tests.unit.models.helpers import create_project, create_user, create_workflow


def test_billing_service_records_usage_and_budget_statuses(db) -> None:
    service = create_billing_service()
    project = create_project(db)
    workflow = create_workflow(db, project=project, status="running")
    node_execution = _create_node_execution(db, workflow.id)
    credential = _create_credential(db, project.owner_id)

    result = asyncio.run(
        service.record_usage_and_check_budget(
            async_db(db),
            workflow_execution_id=workflow.id,
            project_id=project.id,
            user_id=project.owner_id,
            node_execution_id=node_execution.id,
            credential_id=credential.id,
            usage_type="generate",
            model_name="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            budget_config=BudgetConfig(
                max_tokens_per_node=2000,
                max_tokens_per_workflow=2000,
                max_tokens_per_day=2000,
                max_tokens_per_day_per_user=2000,
                warning_threshold=0.5,
                on_exceed="pause",
            ),
        )
    )

    usage = db.query(TokenUsage).one()
    used_tokens = {status.scope: status.used_tokens for status in result.statuses}

    assert usage.estimated_cost == result.usage.estimated_cost
    assert result.usage.total_tokens == 1500
    assert used_tokens == {
        "node": 1500,
        "workflow": 1500,
        "project_day": 1500,
        "user_day": 1500,
    }
    assert all(status.warning_reached for status in result.statuses)
    assert result.exceeded_status is None


def test_billing_service_detects_cross_project_user_daily_budget(db) -> None:
    service = create_billing_service()
    owner = create_user(db)
    project_one = create_project(db, owner=owner)
    project_two = create_project(db, owner=owner)
    workflow_one = create_workflow(db, project=project_one, status="running")
    workflow_two = create_workflow(db, project=project_two, status="running")
    node_one = _create_node_execution(db, workflow_one.id)
    node_two = _create_node_execution(db, workflow_two.id)
    credential = _create_credential(db, owner.id)
    budget = BudgetConfig(
        max_tokens_per_node=1000,
        max_tokens_per_workflow=1000,
        max_tokens_per_day=1000,
        max_tokens_per_day_per_user=100,
        warning_threshold=0.8,
        on_exceed="pause",
    )

    asyncio.run(
        service.record_usage_and_check_budget(
            async_db(db),
            workflow_execution_id=workflow_one.id,
            project_id=project_one.id,
            user_id=owner.id,
            node_execution_id=node_one.id,
            credential_id=credential.id,
            usage_type="generate",
            model_name="gpt-4o",
            input_tokens=20,
            output_tokens=20,
            budget_config=budget,
        )
    )
    result = asyncio.run(
        service.record_usage_and_check_budget(
            async_db(db),
            workflow_execution_id=workflow_two.id,
            project_id=project_two.id,
            user_id=owner.id,
            node_execution_id=node_two.id,
            credential_id=credential.id,
            usage_type="review",
            model_name="gpt-4o",
            input_tokens=30,
            output_tokens=40,
            budget_config=budget,
        )
    )

    assert result.exceeded_status is not None
    assert result.exceeded_status.scope == "user_day"
    assert result.exceeded_status.used_tokens == 110


def test_billing_service_warning_threshold_matches_effective_boundary(db) -> None:
    service = create_billing_service()
    project = create_project(db)
    workflow = create_workflow(db, project=project, status="running")
    node_execution = _create_node_execution(db, workflow.id)
    credential = _create_credential(db, project.owner_id)

    result = asyncio.run(
        service.record_usage_and_check_budget(
            async_db(db),
            workflow_execution_id=workflow.id,
            project_id=project.id,
            user_id=project.owner_id,
            node_execution_id=node_execution.id,
            credential_id=credential.id,
            usage_type="generate",
            model_name="gpt-4o",
            input_tokens=1,
            output_tokens=1,
            budget_config=BudgetConfig(
                max_tokens_per_node=3,
                max_tokens_per_workflow=3,
                max_tokens_per_day=3,
                max_tokens_per_day_per_user=3,
                warning_threshold=0.8,
                on_exceed="pause",
            ),
        )
    )

    assert all(not status.warning_reached for status in result.statuses)
    assert result.exceeded_status is None


def test_billing_service_rejects_missing_llm_usage_tokens(db) -> None:
    service = create_billing_service()
    project = create_project(db)
    workflow = create_workflow(db, project=project, status="running")
    node_execution = _create_node_execution(db, workflow.id)
    credential = _create_credential(db, project.owner_id)

    with pytest.raises(ConfigurationError, match="missing token usage"):
        asyncio.run(
            service.record_usage_and_check_budget(
                async_db(db),
                workflow_execution_id=workflow.id,
                project_id=project.id,
                user_id=project.owner_id,
                node_execution_id=node_execution.id,
                credential_id=credential.id,
                usage_type="generate",
                model_name="gpt-4o",
                input_tokens=None,
                output_tokens=10,
                budget_config=BudgetConfig(),
            )
        )


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


def _create_node_execution(db, workflow_id: uuid.UUID) -> NodeExecution:
    execution = NodeExecution(
        workflow_execution_id=workflow_id,
        node_id="chapter_gen",
        node_type="generate",
        status="running",
        sequence=0,
        node_order=1,
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution
