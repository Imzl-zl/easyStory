from __future__ import annotations

import pytest

from app.modules.observability.models import AuditLog
from app.modules.project.service import (
    ProjectCreateDTO,
    ProjectUpdateDTO,
    ProjectService,
    create_project_management_service,
)
from app.shared.runtime.errors import NotFoundError
from tests.unit.models.helpers import (
    create_project,
    create_template,
    create_user,
    ready_project_setting,
)


def test_project_management_service_creates_lists_gets_and_updates_projects(db) -> None:
    owner = create_user(db)
    template = create_template(db)
    service = create_project_management_service()

    created = service.create_project(
        db,
        ProjectCreateDTO(
            name="新项目",
            template_id=template.id,
            project_setting=ready_project_setting(),
            allow_system_credential_pool=True,
        ),
        owner_id=owner.id,
    )
    summaries = service.list_projects(db, owner_id=owner.id)
    detail = service.get_project(db, created.id, owner_id=owner.id)
    updated = service.update_project(
        db,
        created.id,
        ProjectUpdateDTO(
            name="已改名项目",
            template_id=None,
            allow_system_credential_pool=False,
        ),
        owner_id=owner.id,
    )

    assert created.name == "新项目"
    assert created.template_id == template.id
    assert created.genre == "玄幻"
    assert created.target_words == 800000
    assert len(summaries) == 1
    assert summaries[0].id == created.id
    assert detail.project_setting is not None
    assert detail.project_setting.genre == "玄幻"
    assert updated.name == "已改名项目"
    assert updated.template_id is None
    assert updated.allow_system_credential_pool is False


def test_project_management_service_soft_deletes_and_restores_projects(db) -> None:
    owner = create_user(db)
    project = create_project(db, owner=owner)
    service = create_project_management_service()

    deleted = service.soft_delete_project(db, project.id, owner_id=owner.id)

    assert deleted.deleted_at is not None
    assert service.list_projects(db, owner_id=owner.id) == []
    trash = service.list_projects(db, owner_id=owner.id, deleted_only=True)
    assert len(trash) == 1
    assert trash[0].id == project.id
    with pytest.raises(NotFoundError):
        ProjectService().require_project(db, project.id, owner_id=owner.id)

    restored = service.restore_project(db, project.id, owner_id=owner.id)
    audit_logs = (
        db.query(AuditLog)
        .filter(AuditLog.entity_id == project.id)
        .order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
        .all()
    )

    assert restored.deleted_at is None
    assert len(service.list_projects(db, owner_id=owner.id)) == 1
    assert sorted(item.event_type for item in audit_logs) == [
        "project_delete",
        "project_restore",
    ]
    assert all(item.entity_type == "project" for item in audit_logs)


def test_project_management_service_hides_other_users_projects(db) -> None:
    owner = create_user(db)
    outsider = create_user(db)
    project = create_project(db, owner=owner)
    service = create_project_management_service()

    with pytest.raises(NotFoundError):
        service.get_project(db, project.id, owner_id=outsider.id)
    with pytest.raises(NotFoundError):
        service.soft_delete_project(db, project.id, owner_id=outsider.id)
