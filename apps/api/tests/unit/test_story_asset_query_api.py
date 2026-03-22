from __future__ import annotations

from app.main import create_app
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers as _auth_headers
from tests.unit.models.helpers import create_project, create_user, ready_project_setting


async def test_story_asset_versions_api_returns_outline_history(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="story-asset-query-api")
    )

    try:
        app = create_app(async_session_factory=async_session_factory)
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner, project_setting=ready_project_setting())
            project_id = project.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            await client.put(
                f"/api/v1/projects/{project_id}/outline",
                json={"title": "主线大纲", "content_text": "第一版大纲", "change_summary": "初版"},
                headers=_auth_headers(owner_id),
            )
            await client.put(
                f"/api/v1/projects/{project_id}/outline",
                json={
                    "title": "主线大纲",
                    "content_text": "第二版大纲",
                    "change_summary": "补充伏笔",
                },
                headers=_auth_headers(owner_id),
            )

            response = await client.get(
                f"/api/v1/projects/{project_id}/story-assets/outline/versions",
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 200
        payload = response.json()
        assert [item["version_number"] for item in payload] == [2, 1]
        assert payload[0]["is_current"] is True
        assert payload[0]["change_summary"] == "补充伏笔"
        assert payload[1]["content_text"] == "第一版大纲"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_story_asset_versions_api_hides_other_users_project(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="story-asset-query-api-owner")
    )

    try:
        app = create_app(async_session_factory=async_session_factory)
        with session_factory() as session:
            owner = create_user(session)
            outsider = create_user(session)
            project = create_project(session, owner=owner, project_setting=ready_project_setting())
            project_id = project.id
            owner_id = owner.id
            outsider_id = outsider.id

        async with started_async_client(app) as client:
            await client.put(
                f"/api/v1/projects/{project_id}/outline",
                json={"title": "主线大纲", "content_text": "第一版大纲"},
                headers=_auth_headers(owner_id),
            )

            response = await client.get(
                f"/api/v1/projects/{project_id}/story-assets/outline/versions",
                headers=_auth_headers(outsider_id),
            )

        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
