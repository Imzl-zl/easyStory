from __future__ import annotations

from datetime import UTC, datetime
import uuid

import pytest

from app.modules.observability.models import ExecutionLog, PromptReplay
from app.modules.observability.service import create_workflow_observability_service
from app.modules.workflow.models import NodeExecution
from app.shared.runtime.errors import NotFoundError
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
)
from tests.unit.models.helpers import create_project, create_user, create_workflow


async def test_workflow_observability_service_filters_query_surfaces(
    tmp_path,
) -> None:
    service = create_workflow_observability_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="workflow-observability-query-service")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            workflow = create_workflow(session, project=project, status="paused")
            split_execution = NodeExecution(
                workflow_execution_id=workflow.id,
                node_id="chapter_split",
                sequence=0,
                node_order=0,
                node_type="generate",
                status="completed",
            )
            gen_execution = NodeExecution(
                workflow_execution_id=workflow.id,
                node_id="chapter_gen",
                sequence=0,
                node_order=1,
                node_type="generate",
                status="failed",
            )
            session.add_all([split_execution, gen_execution])
            session.flush()
            first_log_id = uuid.UUID("00000000-0000-0000-0000-000000000011")
            second_log_id = uuid.UUID("00000000-0000-0000-0000-000000000012")
            session.add_all(
                [
                    ExecutionLog(
                        workflow_execution_id=workflow.id,
                        node_execution_id=split_execution.id,
                        level="INFO",
                        message="Split finished",
                        created_at=datetime(2026, 3, 22, 10, 0, tzinfo=UTC),
                    ),
                    ExecutionLog(
                        id=first_log_id,
                        workflow_execution_id=workflow.id,
                        node_execution_id=gen_execution.id,
                        level="ERROR",
                        message="Gen failed",
                        created_at=datetime(2026, 3, 22, 10, 1, tzinfo=UTC),
                    ),
                    ExecutionLog(
                        id=second_log_id,
                        workflow_execution_id=workflow.id,
                        node_execution_id=gen_execution.id,
                        level="INFO",
                        message="Gen retried",
                        created_at=datetime(2026, 3, 22, 10, 2, tzinfo=UTC),
                    ),
                    PromptReplay(
                        node_execution_id=gen_execution.id,
                        replay_type="generate",
                        model_name="gpt-4o",
                        prompt_text="generate prompt",
                        response_text="初稿",
                    ),
                    PromptReplay(
                        node_execution_id=gen_execution.id,
                        replay_type="fix",
                        model_name="gpt-4o",
                        prompt_text="fix prompt",
                        response_text="修订稿",
                    ),
                ]
            )
            session.commit()
            owner_id = owner.id
            workflow_id = workflow.id
            gen_execution_id = gen_execution.id

        async with async_session_factory() as session:
            executions = await service.list_node_executions(
                session,
                workflow_id,
                owner_id=owner_id,
                node_id="chapter_gen",
                status="failed",
            )
            logs = await service.list_execution_logs(
                session,
                workflow_id,
                owner_id=owner_id,
                node_execution_id=gen_execution_id,
                limit=10,
            )
            streamed_logs = await service.list_execution_logs_since(
                session,
                workflow_id,
                owner_id=owner_id,
                node_execution_id=gen_execution_id,
                after_created_at=None,
            )
            replays = await service.list_prompt_replays(
                session,
                workflow_id,
                gen_execution_id,
                owner_id=owner_id,
                replay_type="fix",
            )

        assert [(item.node_id, item.status) for item in executions] == [("chapter_gen", "failed")]
        assert [item.message for item in logs] == ["Gen retried", "Gen failed"]
        assert [item.id for item in streamed_logs] == [first_log_id, second_log_id]
        assert [item.replay_type for item in replays] == ["fix"]
        assert replays[0].response_text == "修订稿"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_workflow_observability_service_rejects_foreign_node_execution_filter(
    tmp_path,
) -> None:
    service = create_workflow_observability_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="workflow-observability-query-scope")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            other_project = create_project(session, owner=owner)
            workflow = create_workflow(session, project=project, status="paused")
            foreign_workflow = create_workflow(session, project=other_project, status="paused")
            foreign_execution = NodeExecution(
                workflow_execution_id=foreign_workflow.id,
                node_id="chapter_gen",
                sequence=0,
                node_order=0,
                node_type="generate",
                status="completed",
            )
            session.add(foreign_execution)
            session.commit()
            owner_id = owner.id
            workflow_id = workflow.id
            foreign_execution_id = foreign_execution.id

        async with async_session_factory() as session:
            with pytest.raises(NotFoundError):
                await service.list_execution_logs(
                    session,
                    workflow_id,
                    owner_id=owner_id,
                    node_execution_id=foreign_execution_id,
                )
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
