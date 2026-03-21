from __future__ import annotations

from app.main import create_app
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers as _auth_headers
from tests.unit.models.helpers import create_content, create_content_version, create_project, create_user


async def test_story_bible_api_creates_lists_and_confirms_conflicts(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="story-bible-api")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            version1 = _create_chapter_version(session, project, chapter_number=1, version_number=1)
            version2 = _create_chapter_version(session, project, chapter_number=2, version_number=1)
            project_id = project.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            created = await client.post(
                f"/api/v1/projects/{project_id}/story-bible",
                json={
                    "chapter_number": 1,
                    "source_content_version_id": str(version1.id),
                    "fact_type": "character_state",
                    "subject": "林渊",
                    "content": "仍是外门弟子",
                },
                headers=_auth_headers(owner_id),
            )
            assert created.status_code == 200
            assert created.json()["action"] == "created"

            conflicted = await client.post(
                f"/api/v1/projects/{project_id}/story-bible",
                json={
                    "chapter_number": 2,
                    "source_content_version_id": str(version2.id),
                    "fact_type": "character_state",
                    "subject": "林渊",
                    "content": "已经进入内门",
                },
                headers=_auth_headers(owner_id),
            )
            assert conflicted.status_code == 200
            conflict_body = conflicted.json()
            assert conflict_body["action"] == "potential_conflict"

            listed = await client.get(
                f"/api/v1/projects/{project_id}/story-bible",
                params={"visible_at_chapter": 1},
                headers=_auth_headers(owner_id),
            )
            assert listed.status_code == 200
            assert [item["chapter_number"] for item in listed.json()] == [1]

            confirmed = await client.post(
                f"/api/v1/projects/{project_id}/story-bible/{conflict_body['fact']['id']}/confirm-conflict",
                headers=_auth_headers(owner_id),
            )
            assert confirmed.status_code == 200
            assert confirmed.json()["action"] == "confirmed_conflict"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_story_bible_api_supports_supersede(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="story-bible-api-supersede")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            chapter = create_content(
                session,
                project=project,
                content_type="chapter",
                chapter_number=5,
                title="第五章",
            )
            version1 = create_content_version(
                session,
                content=chapter,
                version_number=1,
                content_text="初版正文",
                is_current=False,
            )
            version2 = create_content_version(
                session,
                content=chapter,
                version_number=2,
                content_text="第二版正文",
                is_current=True,
            )
            project_id = project.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            created = await client.post(
                f"/api/v1/projects/{project_id}/story-bible",
                json={
                    "chapter_number": 5,
                    "source_content_version_id": str(version1.id),
                    "fact_type": "relationship",
                    "subject": "林渊-沈清",
                    "content": "仍然互不信任",
                },
                headers=_auth_headers(owner_id),
            )
            created_fact_id = created.json()["fact"]["id"]

            conflicted = await client.post(
                f"/api/v1/projects/{project_id}/story-bible",
                json={
                    "chapter_number": 5,
                    "source_content_version_id": str(version2.id),
                    "fact_type": "relationship",
                    "subject": "林渊-沈清",
                    "content": "已经形成合作",
                },
                headers=_auth_headers(owner_id),
            )
            assert conflicted.status_code == 200
            conflict_fact_id = conflicted.json()["fact"]["id"]

            superseded = await client.post(
                f"/api/v1/projects/{project_id}/story-bible/{created_fact_id}/supersede",
                json={"replacement_fact_id": conflict_fact_id},
                headers=_auth_headers(owner_id),
            )
            assert superseded.status_code == 200
            body = superseded.json()
            assert body["action"] == "superseded"
            assert body["related_fact_ids"] == [created_fact_id]
            assert body["fact"]["id"] == conflict_fact_id
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_story_bible_api_hides_other_users_project(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="story-bible-api-owner")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            outsider = create_user(session)
            project = create_project(session, owner=owner)
            project_id = project.id
            outsider_id = outsider.id

        async with started_async_client(app) as client:
            response = await client.get(
                f"/api/v1/projects/{project_id}/story-bible",
                headers=_auth_headers(outsider_id),
            )
            assert response.status_code == 404
            assert response.json()["code"] == "not_found"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_story_bible_api_rejects_foreign_content_version(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="story-bible-api-version")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            other_project = create_project(session, owner=owner)
            foreign_version = _create_chapter_version(
                session,
                other_project,
                chapter_number=3,
                version_number=1,
            )
            project_id = project.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            response = await client.post(
                f"/api/v1/projects/{project_id}/story-bible",
                json={
                    "chapter_number": 3,
                    "source_content_version_id": str(foreign_version.id),
                    "fact_type": "timeline",
                    "subject": "第三卷",
                    "content": "进入山门第三日",
                },
                headers=_auth_headers(owner_id),
            )
            assert response.status_code == 404
            assert response.json()["code"] == "not_found"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def _create_chapter_version(session, project, *, chapter_number: int, version_number: int):
    chapter = create_content(
        session,
        project=project,
        content_type="chapter",
        chapter_number=chapter_number,
        title=f"第{chapter_number}章",
    )
    return create_content_version(
        session,
        content=chapter,
        version_number=version_number,
        content_text=f"第{chapter_number}章正文 v{version_number}",
        is_current=True,
    )
