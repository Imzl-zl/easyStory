from __future__ import annotations

import asyncio

import pytest

from app.modules.content.service import StoryAssetSaveDTO, create_story_asset_service
from app.shared.runtime.errors import NotFoundError
from tests.unit.async_service_support import async_db
from tests.unit.models.helpers import create_project, create_user, ready_project_setting


def test_story_asset_service_lists_versions_in_descending_order(db) -> None:
    owner = create_user(db)
    project = create_project(db, owner=owner, project_setting=ready_project_setting())
    service = create_story_asset_service()

    asyncio.run(
        service.save_asset_draft(
            async_db(db),
            project.id,
            "outline",
            StoryAssetSaveDTO(
                title="主线大纲",
                content_text="第一版大纲",
                change_summary="初版",
            ),
            owner_id=owner.id,
        )
    )
    asyncio.run(
        service.save_asset_draft(
            async_db(db),
            project.id,
            "outline",
            StoryAssetSaveDTO(
                title="主线大纲",
                content_text="第二版大纲",
                change_summary="补充伏笔",
            ),
            owner_id=owner.id,
        )
    )

    versions = asyncio.run(
        service.list_versions(
            async_db(db),
            project.id,
            "outline",
            owner_id=owner.id,
        )
    )

    assert [item.version_number for item in versions] == [2, 1]
    assert versions[0].is_current is True
    assert versions[0].change_summary == "补充伏笔"
    assert versions[1].is_current is False
    assert versions[1].content_text == "第一版大纲"


def test_story_asset_service_rejects_foreign_owner(db) -> None:
    owner = create_user(db)
    outsider = create_user(db)
    project = create_project(db, owner=owner, project_setting=ready_project_setting())
    service = create_story_asset_service()
    asyncio.run(
        service.save_asset_draft(
            async_db(db),
            project.id,
            "outline",
            StoryAssetSaveDTO(title="主线大纲", content_text="第一版大纲"),
            owner_id=owner.id,
        )
    )

    with pytest.raises(NotFoundError, match="Project not found"):
        asyncio.run(
            service.list_versions(
                async_db(db),
                project.id,
                "outline",
                owner_id=outsider.id,
            )
        )
