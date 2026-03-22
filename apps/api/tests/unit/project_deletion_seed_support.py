from __future__ import annotations

from decimal import Decimal

from app.modules.analysis.models import Analysis
from app.modules.billing.models import TokenUsage
from app.modules.context.models import StoryFact
from app.modules.credential.models import ModelCredential
from app.modules.export.models import Export
from app.modules.observability.models import AuditLog, ExecutionLog, PromptReplay
from app.modules.review.models import ReviewAction
from app.modules.workflow.models import Artifact, ChapterTask, NodeExecution
from tests.unit.models.helpers import (
    create_content,
    create_content_version,
    create_project,
    create_user,
    create_workflow,
)


def seed_project_graph(db, *, export_root):
    owner = create_user(db)
    project = create_project(db, owner=owner)
    content = create_content(db, project=project)
    version = create_content_version(db, content=content, content_text="章节正文")
    workflow = create_workflow(db, project=project, status="paused")
    credential_ids = _create_project_credentials(
        db,
        owner_id=owner.id,
        project_id=project.id,
    )
    node = _create_project_node(db, workflow_id=workflow.id)
    export_file = _create_project_export_file(
        export_root,
        project_id=project.id,
        workflow_id=workflow.id,
    )
    related_ids = _create_project_related_records(
        db,
        project_id=project.id,
        content_id=content.id,
        content_version_id=version.id,
        workflow_id=workflow.id,
        node_id=node.id,
        credential_id=credential_ids["project_credential_id"],
        export_file=export_file,
        export_root=export_root,
    )
    return owner, project, {
        **related_ids,
        "content_id": content.id,
        "content_version_id": version.id,
        "node_id": node.id,
        "workflow_id": workflow.id,
    }, credential_ids


def _create_project_credentials(db, *, owner_id, project_id):
    project_credential = ModelCredential(
        owner_type="project",
        owner_id=project_id,
        provider="openai",
        display_name="project-delete-project-key",
        encrypted_key="ciphertext-project",
    )
    system_credential = ModelCredential(
        owner_type="system",
        owner_id=None,
        provider="openai",
        display_name="project-delete-system-key",
        encrypted_key="ciphertext-system",
    )
    db.add_all([project_credential, system_credential])
    db.commit()
    db.refresh(project_credential)
    db.refresh(system_credential)

    db.add(
        AuditLog(
            actor_user_id=owner_id,
            event_type="credential_create",
            entity_type="model_credential",
            entity_id=project_credential.id,
            details={
                "provider": project_credential.provider,
                "owner_type": project_credential.owner_type,
                "owner_id": str(project_id),
            },
        )
    )
    db.commit()
    return {
        "project_credential_id": project_credential.id,
        "system_credential_id": system_credential.id,
    }


def _create_project_node(db, *, workflow_id):
    node = NodeExecution(
        workflow_execution_id=workflow_id,
        node_id="chapter_gen",
        node_type="generate",
        sequence=0,
        node_order=1,
        status="completed",
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


def _create_project_export_file(export_root, *, project_id, workflow_id):
    export_file = export_root / str(project_id) / str(workflow_id) / "novel.md"
    export_file.parent.mkdir(parents=True, exist_ok=True)
    export_file.write_text("导出正文", encoding="utf-8")
    return export_file


def _create_project_related_records(
    db,
    *,
    project_id,
    content_id,
    content_version_id,
    workflow_id,
    node_id,
    credential_id,
    export_file,
    export_root,
):
    content_ids = _create_project_content_records(
        db,
        project_id=project_id,
        content_id=content_id,
        content_version_id=content_version_id,
        workflow_id=workflow_id,
        export_file=export_file,
        export_root=export_root,
    )
    runtime_ids = _create_project_runtime_records(
        db,
        project_id=project_id,
        workflow_id=workflow_id,
        node_id=node_id,
        content_version_id=content_version_id,
        credential_id=credential_id,
    )
    return {**content_ids, **runtime_ids}


def _create_project_content_records(
    db,
    *,
    project_id,
    content_id,
    content_version_id,
    workflow_id,
    export_file,
    export_root,
):
    analysis = Analysis(
        project_id=project_id,
        content_id=content_id,
        analysis_type="plot",
        result={"status": "ok"},
    )
    chapter_task = ChapterTask(
        project_id=project_id,
        workflow_execution_id=workflow_id,
        chapter_number=1,
        title="第一章",
        brief="章节摘要",
        status="completed",
        content_id=content_id,
    )
    story_fact = StoryFact(
        project_id=project_id,
        chapter_number=1,
        source_content_version_id=content_version_id,
        fact_type="character_state",
        subject="林渊",
        content="保持警惕",
    )
    export = Export(
        project_id=project_id,
        format="markdown",
        filename=export_file.name,
        file_path=export_file.relative_to(export_root).as_posix(),
        file_size=export_file.stat().st_size,
        config_snapshot={"workflow_id": str(workflow_id)},
    )
    db.add_all([analysis, chapter_task, story_fact, export])
    db.commit()
    return {
        "analysis_id": analysis.id,
        "chapter_task_id": chapter_task.id,
        "export_id": export.id,
        "story_fact_id": story_fact.id,
    }


def _create_project_runtime_records(
    db,
    *,
    project_id,
    workflow_id,
    node_id,
    content_version_id,
    credential_id,
):
    artifact = Artifact(
        node_execution_id=node_id,
        artifact_type="chapter_draft",
        content_version_id=content_version_id,
        payload={"chapter_number": 1},
    )
    review_action = ReviewAction(
        node_execution_id=node_id,
        agent_id="reviewer-1",
        review_type="consistency",
        status="approved",
    )
    token_usage = TokenUsage(
        project_id=project_id,
        node_execution_id=node_id,
        credential_id=credential_id,
        usage_type="generate",
        model_name="gpt-4.1",
        input_tokens=120,
        output_tokens=240,
        estimated_cost=Decimal("0.003000"),
    )
    db.add_all([artifact, review_action, token_usage])
    db.commit()
    observability_ids = _create_execution_observability_records(
        db,
        workflow_id=workflow_id,
        node_execution_id=node_id,
    )
    return {
        "artifact_id": artifact.id,
        "review_action_id": review_action.id,
        "token_usage_id": token_usage.id,
        **observability_ids,
    }


def _create_execution_observability_records(db, *, workflow_id, node_execution_id):
    execution_log = ExecutionLog(
        workflow_execution_id=workflow_id,
        node_execution_id=node_execution_id,
        level="INFO",
        message="node completed",
        details={"node_id": "chapter_gen"},
    )
    prompt_replay = PromptReplay(
        node_execution_id=node_execution_id,
        replay_type="generate",
        model_name="gpt-4.1",
        prompt_text="生成章节",
        response_text="完成",
        input_tokens=120,
        output_tokens=240,
    )
    db.add_all([execution_log, prompt_replay])
    db.commit()
    return {
        "execution_log_id": execution_log.id,
        "prompt_replay_id": prompt_replay.id,
    }
