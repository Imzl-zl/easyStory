from __future__ import annotations

from datetime import UTC, datetime
import uuid

import pytest

from app.modules.observability.models import ExecutionLog, PromptReplay
from app.modules.observability.service import create_workflow_observability_service
from app.modules.review.models import ReviewAction
from app.modules.workflow.models import Artifact, NodeExecution
from app.shared.runtime.errors import NotFoundError
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
)
from tests.unit.models.helpers import (
    create_content,
    create_content_version,
    create_project,
    create_user,
    create_workflow,
)


async def test_workflow_observability_service_returns_execution_log_and_replay_data(
    tmp_path,
) -> None:
    service = create_workflow_observability_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="workflow-observability-service")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            workflow = create_workflow(session, project=project, status="paused")
            content = create_content(session, project=project)
            version = create_content_version(session, content=content)
            execution = NodeExecution(
                workflow_execution_id=workflow.id,
                node_id="chapter_gen",
                sequence=0,
                node_order=1,
                node_type="generate",
                status="completed",
                input_data={
                    "skill_id": "skill.chapter.xuanhuan",
                    "model_name": "gpt-4o",
                    "provider": "openai",
                    "chapter_number": 1,
                    "prompt": "完整 prompt",
                    "context_report": {"total_tokens": 123, "sections": [{"type": "outline"}]},
                },
                output_data={"chapter_number": 1},
            )
            session.add(execution)
            session.flush()
            session.add(
                Artifact(
                    node_execution_id=execution.id,
                    artifact_type="chapter_content",
                    content_version_id=version.id,
                    payload={"chapter_number": 1},
                    word_count=888,
                )
            )
            session.add(
                ReviewAction(
                    node_execution_id=execution.id,
                    agent_id="agent.style_checker",
                    reviewer_name="文风检查员",
                    review_type="auto_review",
                    status="passed",
                    score=95,
                    summary="通过",
                    issues=[],
                    execution_time_ms=1,
                    tokens_used=10,
                )
            )
            session.add(
                PromptReplay(
                    node_execution_id=execution.id,
                    replay_type="generate",
                    model_name="gpt-4o",
                    prompt_text="完整 prompt",
                    response_text="章节正文",
                    input_tokens=12,
                    output_tokens=34,
                )
            )
            session.add(
                ExecutionLog(
                    workflow_execution_id=workflow.id,
                    node_execution_id=execution.id,
                    level="INFO",
                    message="Node completed",
                    details={"node_id": "chapter_gen"},
                )
            )
            session.commit()
            owner_id = owner.id
            workflow_id = workflow.id
            execution_id = execution.id
            version_id = version.id

        async with async_session_factory() as session:
            executions = await service.list_node_executions(session, workflow_id, owner_id=owner_id)
            logs = await service.list_execution_logs(
                session,
                workflow_id,
                owner_id=owner_id,
                level="INFO",
                limit=10,
            )
            replays = await service.list_prompt_replays(
                session,
                workflow_id,
                execution_id,
                owner_id=owner_id,
            )

        assert len(executions) == 1
        assert executions[0].input_summary == {
            "skill_id": "skill.chapter.xuanhuan",
            "model_name": "gpt-4o",
            "provider": "openai",
            "chapter_number": 1,
        }
        assert executions[0].context_report == {"total_tokens": 123, "sections": [{"type": "outline"}]}
        assert executions[0].artifacts[0].content_version_id == version_id
        assert executions[0].review_actions[0].review_type == "auto_review"
        assert logs[0].message == "Node completed"
        assert replays[0].replay_type == "generate"
        assert replays[0].response_text == "章节正文"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_workflow_observability_service_hides_other_users_data(tmp_path) -> None:
    service = create_workflow_observability_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="workflow-observability-service-owner")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            outsider = create_user(session)
            project = create_project(session, owner=owner)
            workflow = create_workflow(session, project=project, status="paused")
            execution = NodeExecution(
                workflow_execution_id=workflow.id,
                node_id="chapter_split",
                sequence=0,
                node_order=0,
                node_type="generate",
                status="completed",
            )
            session.add(execution)
            session.flush()
            session.add(
                ExecutionLog(
                    workflow_execution_id=workflow.id,
                    node_execution_id=None,
                    level="INFO",
                    message="Workflow started",
                )
            )
            session.add(
                PromptReplay(
                    node_execution_id=execution.id,
                    replay_type="generate",
                    model_name="gpt-4o",
                    prompt_text="p",
                )
            )
            session.commit()
            outsider_id = outsider.id
            workflow_id = workflow.id
            execution_id = execution.id

        async with async_session_factory() as session:
            with pytest.raises(NotFoundError):
                await service.list_execution_logs(session, workflow_id, owner_id=outsider_id)
            with pytest.raises(NotFoundError):
                await service.list_prompt_replays(
                    session,
                    workflow_id,
                    execution_id,
                    owner_id=outsider_id,
                )
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_workflow_observability_service_cursor_keeps_logs_with_same_timestamp(
    tmp_path,
) -> None:
    service = create_workflow_observability_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="workflow-observability-service-cursor")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            workflow = create_workflow(session, project=project, status="running")
            shared_created_at = datetime(2026, 3, 21, 12, 0, tzinfo=UTC)
            first_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
            second_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
            later_id = uuid.UUID("00000000-0000-0000-0000-000000000003")
            session.add_all(
                [
                    ExecutionLog(
                        id=first_id,
                        workflow_execution_id=workflow.id,
                        node_execution_id=None,
                        level="INFO",
                        message="first",
                        created_at=shared_created_at,
                    ),
                    ExecutionLog(
                        id=second_id,
                        workflow_execution_id=workflow.id,
                        node_execution_id=None,
                        level="INFO",
                        message="second",
                        created_at=shared_created_at,
                    ),
                    ExecutionLog(
                        id=later_id,
                        workflow_execution_id=workflow.id,
                        node_execution_id=None,
                        level="INFO",
                        message="later",
                        created_at=datetime(2026, 3, 21, 12, 0, 1, tzinfo=UTC),
                    ),
                ]
            )
            session.commit()
            owner_id = owner.id
            workflow_id = workflow.id

        async with async_session_factory() as session:
            logs = await service.list_execution_logs_since(
                session,
                workflow_id,
                owner_id=owner_id,
                after_created_at=shared_created_at,
                after_id=first_id,
            )

        assert [item.id for item in logs] == [second_id, later_id]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
