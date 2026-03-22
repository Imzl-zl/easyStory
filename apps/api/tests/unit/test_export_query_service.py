from __future__ import annotations

import asyncio

import pytest

from app.modules.export.models import Export
from app.modules.export.service import ExportService
from app.shared.runtime.errors import NotFoundError
from tests.unit.async_service_support import async_db
from tests.unit.models.helpers import create_project, create_user


def test_export_service_returns_export_detail(db, tmp_path) -> None:
    owner = create_user(db)
    project = create_project(db, owner=owner)
    export = Export(
        project_id=project.id,
        format="txt",
        filename="story-export.txt",
        file_path="exports/story-export.txt",
        file_size=123,
        config_snapshot={"template_key": "template.xuanhuan"},
    )
    db.add(export)
    db.commit()
    service = ExportService(tmp_path)

    fetched = asyncio.run(service.get_export(async_db(db), export.id, owner_id=owner.id))
    detail = service.to_detail_dto(fetched)

    assert detail.id == export.id
    assert detail.filename == "story-export.txt"
    assert detail.config_snapshot == {"template_key": "template.xuanhuan"}
    assert detail.updated_at == export.updated_at


def test_export_service_hides_other_users_export_detail(db, tmp_path) -> None:
    owner = create_user(db)
    outsider = create_user(db)
    project = create_project(db, owner=owner)
    export = Export(
        project_id=project.id,
        format="txt",
        filename="story-export.txt",
        file_path="exports/story-export.txt",
    )
    db.add(export)
    db.commit()
    service = ExportService(tmp_path)

    with pytest.raises(NotFoundError):
        asyncio.run(service.get_export(async_db(db), export.id, owner_id=outsider.id))
