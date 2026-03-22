from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.modules.billing.service import create_billing_query_service
from app.shared.runtime.errors import BusinessRuleError, NotFoundError
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
)
from tests.unit.models.helpers import create_project, create_user, create_workflow
from tests.unit.test_billing_query_service import (
    _create_credential,
    _create_node_execution,
    _create_token_usage,
)

FIXED_NOW = datetime(2026, 3, 21, 12, 0, tzinfo=UTC)


async def test_billing_query_service_lists_project_usages_with_filters(tmp_path) -> None:
    service = create_billing_query_service(now_factory=lambda: FIXED_NOW)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="billing-project-query-service")
    )

    try:
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

        async with async_session_factory() as session:
            filtered = await service.list_project_token_usages(
                session,
                project_id,
                owner_id=owner_id,
                workflow_id=workflow_id,
                usage_type="review",
                model_name=" gpt-4o ",
                limit=10,
            )

        assert len(filtered) == 1
        assert filtered[0].workflow_execution_id == workflow_id
        assert filtered[0].usage_type == "review"
        assert filtered[0].model_name == "gpt-4o"
        assert filtered[0].total_tokens == 50
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_billing_query_service_rejects_foreign_or_mismatched_scope(tmp_path) -> None:
    service = create_billing_query_service(now_factory=lambda: FIXED_NOW)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="billing-project-query-scope")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            outsider = create_user(session)
            project = create_project(session, owner=owner)
            other_project = create_project(session, owner=owner)
            workflow = create_workflow(session, project=other_project, status="running")
            project_id = project.id
            outsider_id = outsider.id
            workflow_id = workflow.id
            owner_id = owner.id

        async with async_session_factory() as session:
            with pytest.raises(NotFoundError, match="Project not found"):
                await service.list_project_token_usages(
                    session,
                    project_id,
                    owner_id=outsider_id,
                )
            with pytest.raises(NotFoundError, match="Workflow execution not found"):
                await service.list_project_token_usages(
                    session,
                    project_id,
                    owner_id=owner_id,
                    workflow_id=workflow_id,
                )
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_billing_query_service_rejects_blank_model_name_filter(tmp_path) -> None:
    service = create_billing_query_service(now_factory=lambda: FIXED_NOW)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="billing-project-query-blank")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            project_id = project.id
            owner_id = owner.id

        async with async_session_factory() as session:
            with pytest.raises(BusinessRuleError, match="model_name filter cannot be blank"):
                await service.list_project_token_usages(
                    session,
                    project_id,
                    owner_id=owner_id,
                    model_name="   ",
                )
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
