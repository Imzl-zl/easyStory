from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from app.modules.analysis.models import Analysis
from app.modules.billing.models import TokenUsage
from app.modules.content.models import Content, ContentVersion
from app.modules.context.models import StoryFact
from app.modules.credential.models import ModelCredential
from app.modules.export.models import Export
from app.modules.observability.models import AuditLog, ExecutionLog, PromptReplay
from app.modules.project.models import Project
from app.modules.project.service import (
    ProjectService,
    create_project_deletion_service,
    create_project_management_service,
)
from app.modules.review.models import ReviewAction
from app.modules.workflow.models import Artifact, ChapterTask, NodeExecution, WorkflowExecution
from app.shared.runtime.errors import BusinessRuleError, NotFoundError
from tests.unit.async_service_support import async_db
from tests.unit.models.helpers import (
    create_content,
    create_content_version,
    create_project,
    create_user,
    create_workflow,
)


def test_project_deletion_service_soft_deletes_and_restores_projects(db, tmp_path) -> None:
    owner = create_user(db)
    project = create_project(db, owner=owner)
    deletion_service = create_project_deletion_service(export_root=tmp_path / "exports")
    management_service = create_project_management_service()

    deleted = asyncio.run(
        deletion_service.soft_delete_project(async_db(db), project.id, owner_id=owner.id)
    )

    assert deleted.deleted_at is not None
    assert asyncio.run(management_service.list_projects(async_db(db), owner_id=owner.id)) == []
    trash = asyncio.run(
        management_service.list_projects(async_db(db), owner_id=owner.id, deleted_only=True)
    )
    assert len(trash) == 1
    assert trash[0].id == project.id
    with pytest.raises(NotFoundError):
        asyncio.run(ProjectService().require_project(async_db(db), project.id, owner_id=owner.id))

    restored = asyncio.run(
        deletion_service.restore_project(async_db(db), project.id, owner_id=owner.id)
    )
    audit_logs = (
        db.query(AuditLog)
        .filter(AuditLog.entity_id == project.id)
        .order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
        .all()
    )

    assert restored.deleted_at is None
    assert len(asyncio.run(management_service.list_projects(async_db(db), owner_id=owner.id))) == 1
    assert sorted(item.event_type for item in audit_logs) == [
        "project_delete",
        "project_restore",
    ]
    assert all(item.entity_type == "project" for item in audit_logs)


def test_project_deletion_service_rejects_physical_delete_before_soft_delete(
    db,
    tmp_path,
) -> None:
    owner = create_user(db)
    project = create_project(db, owner=owner)
    service = create_project_deletion_service(export_root=tmp_path / "exports")

    with pytest.raises(BusinessRuleError, match="soft deleted"):
        asyncio.run(service.physical_delete_project(async_db(db), project.id, owner_id=owner.id))


def test_project_deletion_service_physically_deletes_all_related_project_data(
    db,
    tmp_path,
) -> None:
    export_root = tmp_path / "exports"
    owner, project, related_ids, credential_id = _seed_project_graph(db, export_root=export_root)
    service = create_project_deletion_service(export_root=export_root)

    asyncio.run(service.soft_delete_project(async_db(db), project.id, owner_id=owner.id))
    asyncio.run(service.physical_delete_project(async_db(db), project.id, owner_id=owner.id))
    db.expire_all()

    assert db.get(Project, project.id) is None
    assert db.get(Content, related_ids["content_id"]) is None
    assert db.get(ContentVersion, related_ids["content_version_id"]) is None
    assert db.get(Analysis, related_ids["analysis_id"]) is None
    assert db.get(WorkflowExecution, related_ids["workflow_id"]) is None
    assert db.get(NodeExecution, related_ids["node_id"]) is None
    assert db.get(Artifact, related_ids["artifact_id"]) is None
    assert db.get(ReviewAction, related_ids["review_action_id"]) is None
    assert db.get(ChapterTask, related_ids["chapter_task_id"]) is None
    assert db.get(StoryFact, related_ids["story_fact_id"]) is None
    assert db.get(Export, related_ids["export_id"]) is None
    assert db.get(TokenUsage, related_ids["token_usage_id"]) is None
    assert db.get(ExecutionLog, related_ids["execution_log_id"]) is None
    assert db.get(PromptReplay, related_ids["prompt_replay_id"]) is None
    assert db.query(AuditLog).filter(AuditLog.entity_id == project.id).count() == 0
    assert db.get(ModelCredential, credential_id) is not None
    assert not (export_root / str(project.id)).exists()


def test_project_deletion_service_hides_other_users_projects(db, tmp_path) -> None:
    owner = create_user(db)
    outsider = create_user(db)
    project = create_project(db, owner=owner)
    service = create_project_deletion_service(export_root=tmp_path / "exports")

    with pytest.raises(NotFoundError):
        asyncio.run(service.soft_delete_project(async_db(db), project.id, owner_id=outsider.id))
    with pytest.raises(NotFoundError):
        asyncio.run(
            service.physical_delete_project(async_db(db), project.id, owner_id=outsider.id)
        )


def _seed_project_graph(db, *, export_root):
    owner = create_user(db)
    project = create_project(db, owner=owner)
    content = create_content(db, project=project)
    version = create_content_version(db, content=content, content_text="章节正文")
    workflow = create_workflow(db, project=project, status="paused")
    credential = ModelCredential(
        owner_type="system",
        provider="openai",
        display_name="project-delete-test",
        encrypted_key="ciphertext",
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)

    node = NodeExecution(
        workflow_execution_id=workflow.id,
        node_id="chapter_gen",
        node_type="generate",
        sequence=0,
        node_order=1,
        status="completed",
    )
    db.add(node)
    db.commit()
    db.refresh(node)

    export_file = export_root / str(project.id) / str(workflow.id) / "novel.md"
    export_file.parent.mkdir(parents=True, exist_ok=True)
    export_file.write_text("导出正文", encoding="utf-8")

    analysis = Analysis(
        project_id=project.id,
        content_id=content.id,
        analysis_type="plot",
        result={"status": "ok"},
    )
    artifact = Artifact(
        node_execution_id=node.id,
        artifact_type="chapter_draft",
        content_version_id=version.id,
        payload={"chapter_number": 1},
    )
    review_action = ReviewAction(
        node_execution_id=node.id,
        agent_id="reviewer-1",
        review_type="consistency",
        status="approved",
    )
    chapter_task = ChapterTask(
        project_id=project.id,
        workflow_execution_id=workflow.id,
        chapter_number=1,
        title="第一章",
        brief="章节摘要",
        status="completed",
        content_id=content.id,
    )
    story_fact = StoryFact(
        project_id=project.id,
        chapter_number=1,
        source_content_version_id=version.id,
        fact_type="character_state",
        subject="林渊",
        content="保持警惕",
    )
    export = Export(
        project_id=project.id,
        format="markdown",
        filename=export_file.name,
        file_path=export_file.relative_to(export_root).as_posix(),
        file_size=export_file.stat().st_size,
        config_snapshot={"workflow_id": str(workflow.id)},
    )
    token_usage = TokenUsage(
        project_id=project.id,
        node_execution_id=node.id,
        credential_id=credential.id,
        usage_type="generate",
        model_name="gpt-4.1",
        input_tokens=120,
        output_tokens=240,
        estimated_cost=Decimal("0.003000"),
    )
    execution_log = ExecutionLog(
        workflow_execution_id=workflow.id,
        node_execution_id=node.id,
        level="INFO",
        message="node completed",
        details={"node_id": "chapter_gen"},
    )
    prompt_replay = PromptReplay(
        node_execution_id=node.id,
        replay_type="generate",
        model_name="gpt-4.1",
        prompt_text="生成章节",
        response_text="完成",
        input_tokens=120,
        output_tokens=240,
    )
    db.add_all(
        [
            analysis,
            artifact,
            review_action,
            chapter_task,
            story_fact,
            export,
            token_usage,
            execution_log,
            prompt_replay,
        ]
    )
    db.commit()
    return owner, project, {
        "analysis_id": analysis.id,
        "artifact_id": artifact.id,
        "chapter_task_id": chapter_task.id,
        "content_id": content.id,
        "content_version_id": version.id,
        "execution_log_id": execution_log.id,
        "export_id": export.id,
        "node_id": node.id,
        "prompt_replay_id": prompt_replay.id,
        "review_action_id": review_action.id,
        "story_fact_id": story_fact.id,
        "token_usage_id": token_usage.id,
        "workflow_id": workflow.id,
    }, credential.id
