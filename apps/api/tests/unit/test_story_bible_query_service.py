from __future__ import annotations

import asyncio

import pytest

from app.modules.context.service.dto import StoryFactCreateDTO
from app.modules.context.service.story_bible_factory import create_story_bible_service
from app.shared.runtime.errors import NotFoundError
from tests.unit.async_service_support import async_db
from tests.unit.test_story_bible_service import _create_chapter_version
from tests.unit.models.helpers import create_project, create_user


def test_story_bible_service_get_fact_returns_owned_fact(db) -> None:
    owner = create_user(db)
    project = create_project(db, owner=owner)
    version = _create_chapter_version(db, project, chapter_number=1, version_number=1)
    service = create_story_bible_service()
    created = asyncio.run(
        service.create_fact(
            async_db(db),
            project.id,
            StoryFactCreateDTO(
                chapter_number=1,
                source_content_version_id=version.id,
                fact_type="timeline",
                subject="第一卷",
                content="进入宗门第一日",
            ),
            owner_id=owner.id,
        )
    )

    fact = asyncio.run(
        service.get_fact(
            async_db(db),
            project.id,
            created.fact.id,
            owner_id=owner.id,
        )
    )

    assert fact.id == created.fact.id
    assert fact.source_content_version_id == version.id


def test_story_bible_service_list_facts_supports_chapter_and_source_version_filters(db) -> None:
    owner = create_user(db)
    project = create_project(db, owner=owner)
    version1 = _create_chapter_version(db, project, chapter_number=1, version_number=1)
    version2 = _create_chapter_version(db, project, chapter_number=2, version_number=1)
    service = create_story_bible_service()

    first = asyncio.run(
        service.create_fact(
            async_db(db),
            project.id,
            StoryFactCreateDTO(
                chapter_number=1,
                source_content_version_id=version1.id,
                fact_type="timeline",
                subject="第一卷",
                content="进入宗门第一日",
            ),
            owner_id=owner.id,
        )
    )
    second = asyncio.run(
        service.create_fact(
            async_db(db),
            project.id,
            StoryFactCreateDTO(
                chapter_number=2,
                source_content_version_id=version2.id,
                fact_type="timeline",
                subject="第二卷",
                content="进入内门第一日",
            ),
            owner_id=owner.id,
        )
    )

    chapter_facts = asyncio.run(
        service.list_facts(
            async_db(db),
            project.id,
            owner_id=owner.id,
            active_only=False,
            chapter_number=2,
        )
    )
    version_facts = asyncio.run(
        service.list_facts(
            async_db(db),
            project.id,
            owner_id=owner.id,
            active_only=False,
            source_content_version_id=version1.id,
        )
    )

    assert [item.id for item in chapter_facts] == [second.fact.id]
    assert [item.id for item in version_facts] == [first.fact.id]


def test_story_bible_service_get_fact_rejects_foreign_project_fact(db) -> None:
    owner = create_user(db)
    project = create_project(db, owner=owner)
    other_project = create_project(db, owner=owner)
    version = _create_chapter_version(db, other_project, chapter_number=1, version_number=1)
    service = create_story_bible_service()
    created = asyncio.run(
        service.create_fact(
            async_db(db),
            other_project.id,
            StoryFactCreateDTO(
                chapter_number=1,
                source_content_version_id=version.id,
                fact_type="timeline",
                subject="第一卷",
                content="进入宗门第一日",
            ),
            owner_id=owner.id,
        )
    )

    with pytest.raises(NotFoundError, match="StoryFact not found"):
        asyncio.run(
            service.get_fact(
                async_db(db),
                project.id,
                created.fact.id,
                owner_id=owner.id,
            )
        )
