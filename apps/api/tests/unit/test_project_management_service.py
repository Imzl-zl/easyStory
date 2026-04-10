from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select

from app.modules.project.infrastructure import ProjectDocumentFileStore
from app.modules.content.models import Content
from app.modules.project.service import (
    ProjectCreateDTO,
    ProjectService,
    ProjectUpdateDTO,
    create_project_management_service,
)
from app.shared.runtime.errors import NotFoundError
from tests.unit.async_service_support import async_db
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

    created = asyncio.run(
        service.create_project(
            async_db(db),
            ProjectCreateDTO(
                name="新项目",
                template_id=template.id,
                project_setting=ready_project_setting(),
                allow_system_credential_pool=True,
            ),
            owner_id=owner.id,
        )
    )
    summaries = asyncio.run(service.list_projects(async_db(db), owner_id=owner.id))
    detail = asyncio.run(service.get_project(async_db(db), created.id, owner_id=owner.id))
    updated = asyncio.run(
        service.update_project(
            async_db(db),
            created.id,
            ProjectUpdateDTO(
                name="已改名项目",
                template_id=None,
                allow_system_credential_pool=False,
            ),
            owner_id=owner.id,
        ),
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


def test_project_management_service_hides_other_users_projects(db) -> None:
    owner = create_user(db)
    outsider = create_user(db)
    project = create_project(db, owner=owner)
    service = create_project_management_service()

    with pytest.raises(NotFoundError):
        asyncio.run(service.get_project(async_db(db), project.id, owner_id=outsider.id))


def test_project_management_service_scaffolds_preparation_assets_on_create(db) -> None:
    owner = create_user(db)
    service = create_project_management_service()

    created = asyncio.run(
        service.create_project(
            async_db(db),
            ProjectCreateDTO(name="带骨架项目"),
            owner_id=owner.id,
        )
    )

    contents = (
        db.execute(
            select(Content)
            .where(Content.project_id == created.id)
            .order_by(Content.content_type.asc())
        )
        .scalars()
        .all()
    )

    assert [content.content_type for content in contents] == ["opening_plan", "outline"]
    assert [content.title for content in contents] == ["开篇设计", "大纲"]
    assert all(content.status == "draft" for content in contents)
    assert all(len(content.versions) == 1 for content in contents)
    assert all(content.versions[0].version_number == 1 for content in contents)
    assert all(content.versions[0].content_text == "" for content in contents)


def test_project_management_service_seeds_project_overview_document_from_setting(db, tmp_path) -> None:
    owner = create_user(db)
    file_store = ProjectDocumentFileStore(tmp_path)
    project_service = ProjectService(document_file_store=file_store)

    class StubStoryAssetService:
        async def scaffold_preparation_assets(self, db, project_id):
            return None

    service = create_project_management_service(
        project_service=project_service,
        story_asset_service=StubStoryAssetService(),
    )

    created = asyncio.run(
        service.create_project(
            async_db(db),
            ProjectCreateDTO(
                name="带说明项目",
                project_setting=ready_project_setting(),
            ),
            owner_id=owner.id,
        )
    )

    overview = file_store.find_project_document(created.id, "项目说明.md")

    assert overview is not None
    assert "# 项目说明" in overview.content
    assert "项目名称：带说明项目" in overview.content
    assert "题材：玄幻" in overview.content
