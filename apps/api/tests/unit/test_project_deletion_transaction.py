from __future__ import annotations

import asyncio

import pytest

from app.modules.project.models import Project
from app.modules.project.service import create_project_deletion_service
from tests.unit.async_service_support import AsyncSessionAdapter, async_db
from tests.unit.project_deletion_seed_support import seed_project_graph


class _CommitFailingAsyncSession(AsyncSessionAdapter):
    async def commit(self) -> None:
        raise RuntimeError("commit failed")


def test_physical_delete_keeps_export_directory_when_commit_fails(db, tmp_path) -> None:
    export_root = tmp_path / "exports"
    owner, project, _, _ = seed_project_graph(db, export_root=export_root)
    service = create_project_deletion_service(export_root=export_root)
    project_export_dir = export_root / str(project.id)

    asyncio.run(service.soft_delete_project(async_db(db), project.id, owner_id=owner.id))
    assert project_export_dir.exists()

    with pytest.raises(RuntimeError, match="commit failed"):
        asyncio.run(
            service.physical_delete_project(
                _CommitFailingAsyncSession(db),
                project.id,
                owner_id=owner.id,
            )
        )

    db.expire_all()
    assert db.get(Project, project.id) is not None
    assert project_export_dir.exists()
