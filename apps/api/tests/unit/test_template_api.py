from __future__ import annotations

from app.main import create_app
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers as _auth_headers
from tests.unit.models.helpers import create_user


async def test_template_api_lists_and_reads_builtin_templates_after_startup(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="template-api")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id

        app = create_app(
            async_session_factory=async_session_factory,
        )
        async with started_async_client(app) as client:
            list_response = await client.get("/api/v1/templates", headers=_auth_headers(owner_id))
            assert list_response.status_code == 200
            templates = list_response.json()
            assert len(templates) == 1
            assert templates[0]["name"] == "玄幻小说模板"
            assert templates[0]["workflow_id"] == "workflow.xuanhuan_manual"

            detail_response = await client.get(
                f"/api/v1/templates/{templates[0]['id']}",
                headers=_auth_headers(owner_id),
            )
            assert detail_response.status_code == 200
            detail = detail_response.json()
            assert detail["config"]["template_key"] == "template.xuanhuan"
            export_node = next(node for node in detail["nodes"] if node["node_id"] == "export")
            assert export_node["skill_id"] is None
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_template_api_requires_authentication(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="template-api-auth")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        async with started_async_client(app) as client:
            response = await client.get("/api/v1/templates")
            assert response.status_code == 401
            assert response.json()["code"] == "unauthorized"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
