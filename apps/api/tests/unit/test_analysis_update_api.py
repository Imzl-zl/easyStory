from __future__ import annotations

from app.main import create_app
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers as _auth_headers
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.models.helpers import create_content, create_project, create_user


async def test_analysis_api_updates_analysis(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-api-update")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            content = create_content(session, project=project, title="第六章：河谷回声")
            project_id = project.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            create_response = await client.post(
                f"/api/v1/projects/{project_id}/analyses",
                json={
                    "content_id": str(content.id),
                    "analysis_type": "style",
                    "source_title": "旧标题",
                    "result": {"writing_style": {"vocabulary": "克制"}},
                    "suggestions": {"keep": ["留白"]},
                },
                headers=_auth_headers(owner_id),
            )
            assert create_response.status_code == 200
            analysis_id = create_response.json()["id"]

            update_response = await client.patch(
                f"/api/v1/projects/{project_id}/analyses/{analysis_id}",
                json={
                    "source_title": "   ",
                    "analysis_scope": {"mode": "sample", "picked_chapters": [2, 4]},
                    "result": {"writing_style": {"rhythm": "steady"}},
                    "suggestions": None,
                    "generated_skill_key": " skill.style.river ",
                },
                headers=_auth_headers(owner_id),
            )
            assert update_response.status_code == 200
            updated = update_response.json()
            assert updated["source_title"] == "第六章：河谷回声"
            assert updated["analysis_scope"] == {"mode": "sample", "picked_chapters": [2, 4]}
            assert updated["result"]["writing_style"]["rhythm"] == "steady"
            assert updated["suggestions"] is None
            assert updated["generated_skill_key"] == "skill.style.river"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_analysis_api_hides_other_users_project_on_update(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-api-update-owner")
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

            update_response = await client.patch(
                f"/api/v1/projects/{project_id}/analyses/{analysis_id}",
                json={"result": {"structure": "单线推进"}},
                headers=_auth_headers(outsider_id),
            )
            assert update_response.status_code == 404
            assert update_response.json()["code"] == "not_found"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_analysis_api_rejects_clearing_source_title_without_content(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-api-update-traceability")
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

            update_response = await client.patch(
                f"/api/v1/projects/{project_id}/analyses/{analysis_id}",
                json={"source_title": "   "},
                headers=_auth_headers(owner_id),
            )
            assert update_response.status_code == 422
            assert update_response.json()["code"] == "business_rule_error"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
