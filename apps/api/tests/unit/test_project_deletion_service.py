from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
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
from tests.unit.project_deletion_seed_support import seed_project_graph
from tests.unit.async_service_support import async_db
from tests.unit.models.helpers import create_project, create_user


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
    owner, project, related_ids, credential_ids = seed_project_graph(
        db,
        export_root=export_root,
    )
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
    assert db.query(AuditLog).filter(
        AuditLog.entity_id == credential_ids["project_credential_id"]
    ).count() == 0
    assert db.get(ModelCredential, credential_ids["project_credential_id"]) is None
    assert db.get(ModelCredential, credential_ids["system_credential_id"]) is not None
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


def test_project_deletion_service_empties_only_current_owner_trash(db, tmp_path) -> None:
    owner = create_user(db)
    outsider = create_user(db)
    now = datetime.now(UTC)
    owned_first = create_project(db, owner=owner)
    owned_second = create_project(db, owner=owner)
    owned_active = create_project(db, owner=owner)
    outsider_deleted = create_project(db, owner=outsider)
    owned_first.deleted_at = now
    owned_second.deleted_at = now
    outsider_deleted.deleted_at = now
    db.commit()
    service = create_project_deletion_service(export_root=tmp_path / "exports")

    result = asyncio.run(service.empty_trash(async_db(db), owner_id=owner.id))

    assert result.deleted_count == 2
    assert db.get(Project, owned_first.id) is None
    assert db.get(Project, owned_second.id) is None
    assert db.get(Project, owned_active.id) is not None
    assert db.get(Project, outsider_deleted.id) is not None


def test_project_deletion_service_cleans_only_expired_projects(db, tmp_path) -> None:
    owner = create_user(db)
    now = datetime.now(UTC)
    expired_project = create_project(db, owner=owner)
    retained_project = create_project(db, owner=owner)
    expired_project.deleted_at = now - timedelta(days=31)
    retained_project.deleted_at = now - timedelta(days=5)
    db.commit()
    service = create_project_deletion_service(export_root=tmp_path / "exports")

    result = asyncio.run(
        service.cleanup_expired_projects(
            async_db(db),
            now=now,
            retention_days=30,
        )
    )

    assert result.deleted_count == 1
    assert db.get(Project, expired_project.id) is None
    assert db.get(Project, retained_project.id) is not None
