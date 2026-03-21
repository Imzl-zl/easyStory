from __future__ import annotations

from datetime import UTC, datetime
import uuid

import pytest

from app.modules.observability.models import ExecutionLog, PromptReplay
from app.modules.observability.service import WorkflowObservabilityService
from app.modules.review.models import ReviewAction
from app.modules.workflow.models import Artifact, NodeExecution
from app.shared.runtime.errors import NotFoundError
from tests.unit.models.helpers import (
    create_content,
    create_content_version,
    create_project,
    create_user,
    create_workflow,
)


def test_workflow_observability_service_returns_execution_log_and_replay_data(db) -> None:
    owner = create_user(db)
    project = create_project(db, owner=owner)
    workflow = create_workflow(db, project=project, status="paused")
    content = create_content(db, project=project)
    version = create_content_version(db, content=content)
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
    db.add(execution)
    db.flush()
    db.add(
        Artifact(
            node_execution_id=execution.id,
            artifact_type="chapter_content",
            content_version_id=version.id,
            payload={"chapter_number": 1},
            word_count=888,
        )
    )
    db.add(
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
    db.add(
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
    db.add(
        ExecutionLog(
            workflow_execution_id=workflow.id,
            node_execution_id=execution.id,
            level="INFO",
            message="Node completed",
            details={"node_id": "chapter_gen"},
        )
    )
    db.commit()

    service = WorkflowObservabilityService()
    executions = service.list_node_executions(db, workflow.id, owner_id=owner.id)
    logs = service.list_execution_logs(db, workflow.id, owner_id=owner.id, level="INFO", limit=10)
    replays = service.list_prompt_replays(db, workflow.id, execution.id, owner_id=owner.id)

    assert len(executions) == 1
    assert executions[0].input_summary == {
        "skill_id": "skill.chapter.xuanhuan",
        "model_name": "gpt-4o",
        "provider": "openai",
        "chapter_number": 1,
    }
    assert executions[0].context_report == {"total_tokens": 123, "sections": [{"type": "outline"}]}
    assert executions[0].artifacts[0].content_version_id == version.id
    assert executions[0].review_actions[0].review_type == "auto_review"
    assert logs[0].message == "Node completed"
    assert replays[0].replay_type == "generate"
    assert replays[0].response_text == "章节正文"


def test_workflow_observability_service_hides_other_users_data(db) -> None:
    owner = create_user(db)
    outsider = create_user(db)
    project = create_project(db, owner=owner)
    workflow = create_workflow(db, project=project, status="paused")
    execution = NodeExecution(
        workflow_execution_id=workflow.id,
        node_id="chapter_split",
        sequence=0,
        node_order=0,
        node_type="generate",
        status="completed",
    )
    db.add(execution)
    db.flush()
    db.add(
        ExecutionLog(
            workflow_execution_id=workflow.id,
            node_execution_id=None,
            level="INFO",
            message="Workflow started",
        )
    )
    db.add(
        PromptReplay(
            node_execution_id=execution.id,
            replay_type="generate",
            model_name="gpt-4o",
            prompt_text="p",
        )
    )
    db.commit()

    service = WorkflowObservabilityService()

    with pytest.raises(NotFoundError):
        service.list_execution_logs(db, workflow.id, owner_id=outsider.id)
    with pytest.raises(NotFoundError):
        service.list_prompt_replays(db, workflow.id, execution.id, owner_id=outsider.id)


def test_workflow_observability_service_cursor_keeps_logs_with_same_timestamp(db) -> None:
    owner = create_user(db)
    project = create_project(db, owner=owner)
    workflow = create_workflow(db, project=project, status="running")
    shared_created_at = datetime(2026, 3, 21, 12, 0, tzinfo=UTC)
    first_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    second_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    later_id = uuid.UUID("00000000-0000-0000-0000-000000000003")
    db.add_all(
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
    db.commit()

    service = WorkflowObservabilityService()

    logs = service.list_execution_logs_since(
        db,
        workflow.id,
        owner_id=owner.id,
        after_created_at=shared_created_at,
        after_id=first_id,
    )

    assert [item.id for item in logs] == [second_id, later_id]
