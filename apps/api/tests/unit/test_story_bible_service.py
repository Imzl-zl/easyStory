from __future__ import annotations

import asyncio

import pytest

from app.modules.context.models import StoryFact
from app.modules.context.service import (
    StoryFactConflictStatus,
    StoryFactCreateDTO,
    StoryFactCreateResolution,
    StoryFactMutationAction,
    create_story_bible_service,
)
from app.shared.runtime.errors import BusinessRuleError
from tests.unit.async_service_support import async_db
from tests.unit.models.helpers import create_content, create_content_version, create_project, create_user


def test_story_bible_service_creates_lists_and_confirms_conflicts(db) -> None:
    owner = create_user(db)
    project = create_project(db, owner=owner)
    version1 = _create_chapter_version(db, project, chapter_number=1, version_number=1)
    version2 = _create_chapter_version(db, project, chapter_number=2, version_number=1)
    service = create_story_bible_service()

    created = asyncio.run(
        service.create_fact(
            async_db(db),
            project.id,
            StoryFactCreateDTO(
                chapter_number=1,
                source_content_version_id=version1.id,
                fact_type="character_state",
                subject="林渊",
                content="仍是外门弟子",
            ),
            owner_id=owner.id,
        )
    )
    duplicate = asyncio.run(
        service.create_fact(
            async_db(db),
            project.id,
            StoryFactCreateDTO(
                chapter_number=1,
                source_content_version_id=version1.id,
                fact_type="character_state",
                subject="林渊",
                content="仍是外门弟子",
            ),
            owner_id=owner.id,
        )
    )
    conflicted = asyncio.run(
        service.create_fact(
            async_db(db),
            project.id,
            StoryFactCreateDTO(
                chapter_number=2,
                source_content_version_id=version2.id,
                fact_type="character_state",
                subject="林渊",
                content="已经进入内门",
            ),
            owner_id=owner.id,
        )
    )
    visible_at_first_chapter = asyncio.run(
        service.list_facts(
            async_db(db),
            project.id,
            owner_id=owner.id,
            visible_at_chapter=1,
        )
    )

    assert created.action == StoryFactMutationAction.CREATED
    assert duplicate.action == StoryFactMutationAction.DUPLICATE
    assert conflicted.action == StoryFactMutationAction.POTENTIAL_CONFLICT
    assert [item.id for item in visible_at_first_chapter] == [created.fact.id]

    confirmed = asyncio.run(
        service.confirm_conflict(
            async_db(db),
            project.id,
            conflicted.fact.id,
            owner_id=owner.id,
        )
    )
    left = db.get(StoryFact, created.fact.id)
    right = db.get(StoryFact, conflicted.fact.id)

    assert confirmed.action == StoryFactMutationAction.CONFIRMED_CONFLICT
    assert left is not None and left.conflict_status == StoryFactConflictStatus.CONFIRMED.value
    assert right is not None and right.conflict_status == StoryFactConflictStatus.CONFIRMED.value


def test_story_bible_service_supports_supersede_and_restore_version_view(db) -> None:
    owner = create_user(db)
    project = create_project(db, owner=owner)
    chapter = create_content(
        db,
        project=project,
        content_type="chapter",
        chapter_number=5,
        title="第五章",
    )
    version1 = create_content_version(
        db,
        content=chapter,
        version_number=1,
        content_text="初版正文",
        is_current=False,
    )
    version2 = create_content_version(
        db,
        content=chapter,
        version_number=2,
        content_text="第二版正文",
        is_current=True,
    )
    service = create_story_bible_service()

    created = asyncio.run(
        service.create_fact(
            async_db(db),
            project.id,
            StoryFactCreateDTO(
                chapter_number=5,
                source_content_version_id=version1.id,
                fact_type="relationship",
                subject="林渊-沈清",
                content="仍然互不信任",
            ),
            owner_id=owner.id,
        )
    )
    superseded = asyncio.run(
        service.create_fact(
            async_db(db),
            project.id,
            StoryFactCreateDTO(
                chapter_number=5,
                source_content_version_id=version2.id,
                fact_type="relationship",
                subject="林渊-沈清",
                content="已经形成合作",
                resolution=StoryFactCreateResolution.SUPERSEDE,
                supersede_fact_id=created.fact.id,
            ),
            owner_id=owner.id,
        )
    )

    assert superseded.action == StoryFactMutationAction.SUPERSEDED

    asyncio.run(
        service.restore_version_facts(
            async_db(db),
            project_id=project.id,
            chapter_number=5,
            source_content_version_id=version1.id,
        )
    )
    db.commit()

    old_fact = db.get(StoryFact, created.fact.id)
    new_fact = db.get(StoryFact, superseded.fact.id)

    assert old_fact is not None and old_fact.is_active is True
    assert old_fact.superseded_by is None
    assert new_fact is not None and new_fact.is_active is False


def test_story_bible_service_rejects_supersede_without_active_fact(db) -> None:
    owner = create_user(db)
    project = create_project(db, owner=owner)
    version1 = _create_chapter_version(db, project, chapter_number=1, version_number=1)
    service = create_story_bible_service()

    with pytest.raises(BusinessRuleError, match="没有可 supersede"):
        asyncio.run(
            service.create_fact(
                async_db(db),
                project.id,
                StoryFactCreateDTO(
                    chapter_number=1,
                    source_content_version_id=version1.id,
                    fact_type="timeline",
                    subject="第一卷",
                    content="进入宗门第一日",
                    resolution=StoryFactCreateResolution.SUPERSEDE,
                    supersede_fact_id=version1.id,
                ),
                owner_id=owner.id,
            )
        )


def _create_chapter_version(db, project, *, chapter_number: int, version_number: int):
    chapter = create_content(
        db,
        project=project,
        content_type="chapter",
        chapter_number=chapter_number,
        title=f"第{chapter_number}章",
    )
    return create_content_version(
        db,
        content=chapter,
        version_number=version_number,
        content_text=f"第{chapter_number}章正文 v{version_number}",
        is_current=True,
    )
