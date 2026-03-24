from __future__ import annotations

from app.main import create_app
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers as _auth_headers
from tests.unit.test_story_bible_api import _create_chapter_version
from tests.unit.models.helpers import create_project, create_user


async def test_story_bible_api_supports_detail_and_precise_filters(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="story-bible-query-api")
    )

    try:
        app = create_app(async_session_factory=async_session_factory)
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            version1 = _create_chapter_version(session, project, chapter_number=1, version_number=1)
            version2 = _create_chapter_version(session, project, chapter_number=2, version_number=1)
            project_id = project.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            first = await client.post(
                f"/api/v1/projects/{project_id}/story-bible",
                json={
                    "chapter_number": 1,
                    "source_content_version_id": str(version1.id),
                    "fact_type": "timeline",
                    "subject": "第一卷",
                    "content": "进入宗门第一日",
                },
                headers=_auth_headers(owner_id),
            )
            second = await client.post(
                f"/api/v1/projects/{project_id}/story-bible",
                json={
                    "chapter_number": 2,
                    "source_content_version_id": str(version2.id),
                    "fact_type": "timeline",
                    "subject": "第二卷",
                    "content": "进入内门第一日",
                },
                headers=_auth_headers(owner_id),
            )
            first_fact_id = first.json()["fact"]["id"]

            detail = await client.get(
                f"/api/v1/projects/{project_id}/story-bible/{first_fact_id}",
                headers=_auth_headers(owner_id),
            )
            chapter_filtered = await client.get(
                f"/api/v1/projects/{project_id}/story-bible",
                params={"active_only": "false", "chapter_number": 2},
                headers=_auth_headers(owner_id),
            )
            version_filtered = await client.get(
                f"/api/v1/projects/{project_id}/story-bible",
                params={"active_only": "false", "source_content_version_id": str(version1.id)},
                headers=_auth_headers(owner_id),
            )

            assert detail.status_code == 200
            assert detail.json()["id"] == first_fact_id
            assert detail.json()["source_content_version_id"] == str(version1.id)
            assert chapter_filtered.status_code == 200
            assert [item["id"] for item in chapter_filtered.json()] == [second.json()["fact"]["id"]]
            assert version_filtered.status_code == 200
            assert [item["id"] for item in version_filtered.json()] == [first_fact_id]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_story_bible_api_hides_fact_detail_from_other_user(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="story-bible-query-api-owner")
    )

    try:
        app = create_app(async_session_factory=async_session_factory)
        with session_factory() as session:
            owner = create_user(session)
            outsider = create_user(session)
            project = create_project(session, owner=owner)
            version = _create_chapter_version(session, project, chapter_number=1, version_number=1)
            project_id = project.id
            owner_id = owner.id
            outsider_id = outsider.id

        async with started_async_client(app) as client:
            created = await client.post(
                f"/api/v1/projects/{project_id}/story-bible",
                json={
                    "chapter_number": 1,
                    "source_content_version_id": str(version.id),
                    "fact_type": "timeline",
                    "subject": "第一卷",
                    "content": "进入宗门第一日",
                },
                headers=_auth_headers(owner_id),
            )
            fact_id = created.json()["fact"]["id"]

            response = await client.get(
                f"/api/v1/projects/{project_id}/story-bible/{fact_id}",
                headers=_auth_headers(outsider_id),
            )

            assert response.status_code == 404
            assert response.json()["code"] == "not_found"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
