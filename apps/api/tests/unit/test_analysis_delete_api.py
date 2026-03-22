from __future__ import annotations

from app.main import create_app
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers as _auth_headers
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.models.helpers import create_project, create_user


async def test_analysis_api_deletes_analysis(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-api-delete")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            project_id = project.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            create_response = await client.post(
                f"/api/v1/projects/{project_id}/analyses",
                json={
                    "analysis_type": "plot",
                    "source_title": "样例小说",
                    "result": {"structure": "双线叙事"},
                },
                headers=_auth_headers(owner_id),
            )
            assert create_response.status_code == 200
            analysis_id = create_response.json()["id"]

            delete_response = await client.delete(
                f"/api/v1/projects/{project_id}/analyses/{analysis_id}",
                headers=_auth_headers(owner_id),
            )
            assert delete_response.status_code == 204

            detail_response = await client.get(
                f"/api/v1/projects/{project_id}/analyses/{analysis_id}",
                headers=_auth_headers(owner_id),
            )
            assert detail_response.status_code == 404
            assert detail_response.json()["code"] == "not_found"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_analysis_api_hides_other_users_project_on_delete(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-api-delete-owner")
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
            owner_id = owner.id
            outsider_id = outsider.id

        async with started_async_client(app) as client:
            create_response = await client.post(
                f"/api/v1/projects/{project_id}/analyses",
                json={
                    "analysis_type": "plot",
                    "source_title": "样例小说",
                    "result": {"structure": "双线叙事"},
                },
                headers=_auth_headers(owner_id),
            )
            assert create_response.status_code == 200
            analysis_id = create_response.json()["id"]

            delete_response = await client.delete(
                f"/api/v1/projects/{project_id}/analyses/{analysis_id}",
                headers=_auth_headers(outsider_id),
            )
            assert delete_response.status_code == 404
            assert delete_response.json()["code"] == "not_found"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
