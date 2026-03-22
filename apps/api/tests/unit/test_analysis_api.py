from __future__ import annotations

from app.main import create_app
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers as _auth_headers
from tests.unit.models.helpers import create_content, create_project, create_user


async def test_analysis_api_creates_lists_and_gets_analysis(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-api")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            content = create_content(session, project=project, title="第一章")
            project_id = project.id
            content_id = content.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            create_response = await client.post(
                f"/api/v1/projects/{project_id}/analyses",
                json={
                    "content_id": str(content_id),
                    "analysis_type": "style",
                    "source_title": "样例小说",
                    "analysis_scope": {"mode": "chapter_range", "chapters": [1, 2]},
                    "result": {"writing_style": {"vocabulary": "华丽"}},
                    "suggestions": {"keep": ["对话感"]},
                },
                headers=_auth_headers(owner_id),
            )
            assert create_response.status_code == 200
            created = create_response.json()
            assert created["analysis_type"] == "style"
            assert created["content_id"] == str(content_id)

            list_response = await client.get(
                f"/api/v1/projects/{project_id}/analyses",
                params={"analysis_type": "style", "content_id": str(content_id)},
                headers=_auth_headers(owner_id),
            )
            assert list_response.status_code == 200
            listed = list_response.json()
            assert len(listed) == 1
            assert listed[0]["id"] == created["id"]

            detail_response = await client.get(
                f"/api/v1/projects/{project_id}/analyses/{created['id']}",
                headers=_auth_headers(owner_id),
            )
            assert detail_response.status_code == 200
            detail = detail_response.json()
            assert detail["result"]["writing_style"]["vocabulary"] == "华丽"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_analysis_api_filters_by_generated_skill_key(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-api-skill-key")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            content = create_content(session, project=project, title="第一章")
            project_id = project.id
            content_id = content.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            first_response = await client.post(
                f"/api/v1/projects/{project_id}/analyses",
                json={
                    "content_id": str(content_id),
                    "analysis_type": "style",
                    "source_title": "样例小说",
                    "result": {"writing_style": {"vocabulary": "华丽"}},
                    "generated_skill_key": "skill.style.river",
                },
                headers=_auth_headers(owner_id),
            )
            assert first_response.status_code == 200

            second_response = await client.post(
                f"/api/v1/projects/{project_id}/analyses",
                json={
                    "content_id": str(content_id),
                    "analysis_type": "style",
                    "source_title": "样例小说",
                    "result": {"writing_style": {"vocabulary": "克制"}},
                    "generated_skill_key": "skill.style.forest",
                },
                headers=_auth_headers(owner_id),
            )
            assert second_response.status_code == 200

            list_response = await client.get(
                f"/api/v1/projects/{project_id}/analyses",
                params={"generated_skill_key": " skill.style.river "},
                headers=_auth_headers(owner_id),
            )
            assert list_response.status_code == 200
            listed = list_response.json()
            assert len(listed) == 1
            assert listed[0]["generated_skill_key"] == "skill.style.river"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_analysis_api_hides_other_users_project(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-api-owner")
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
                f"/api/v1/projects/{project_id}/analyses",
                headers=_auth_headers(outsider_id),
            )
            assert response.status_code == 404
            assert response.json()["code"] == "not_found"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_analysis_api_rejects_blank_generated_skill_key_filter(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-api-skill-key-blank")
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
            response = await client.get(
                f"/api/v1/projects/{project_id}/analyses",
                params={"generated_skill_key": "   "},
                headers=_auth_headers(owner_id),
            )
            assert response.status_code == 422
            assert response.json()["code"] == "business_rule_error"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_analysis_api_rejects_foreign_content_reference(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-api-content")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            other_project = create_project(session, owner=owner)
            foreign_content = create_content(session, project=other_project)
            project_id = project.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            response = await client.post(
                f"/api/v1/projects/{project_id}/analyses",
                json={
                    "content_id": str(foreign_content.id),
                    "analysis_type": "style",
                    "result": {"writing_style": {"vocabulary": "华丽"}},
                },
                headers=_auth_headers(owner_id),
            )
            assert response.status_code == 404
            assert response.json()["code"] == "not_found"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_analysis_api_backfills_source_title_from_content_title(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-api-source-title")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            content = create_content(session, project=project, title="第三章：渡口")
            project_id = project.id
            owner_id = owner.id

        async with started_async_client(app) as client:
            response = await client.post(
                f"/api/v1/projects/{project_id}/analyses",
                json={
                    "content_id": str(content.id),
                    "analysis_type": "style",
                    "source_title": "   ",
                    "result": {"writing_style": {"vocabulary": "克制"}},
                },
                headers=_auth_headers(owner_id),
            )
            assert response.status_code == 200
            assert response.json()["source_title"] == "第三章：渡口"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_analysis_api_rejects_missing_traceability_source(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="analysis-api-traceability")
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
            response = await client.post(
                f"/api/v1/projects/{project_id}/analyses",
                json={
                    "analysis_type": "plot",
                    "result": {"structure": "双线叙事"},
                },
                headers=_auth_headers(owner_id),
            )
            assert response.status_code == 422
            assert response.json()["detail"][0]["type"] == "value_error"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
