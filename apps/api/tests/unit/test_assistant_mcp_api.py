from __future__ import annotations

from app.main import create_app
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.models.helpers import create_project, create_user


async def test_assistant_mcp_api_crud(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(
        "EASYSTORY_ASSISTANT_CONFIG_ROOT",
        str(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-mcp-api")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        app = create_app(async_session_factory=async_session_factory)

        async with started_async_client(app) as client:
            initial = await client.get("/api/v1/assistant/mcp_servers", headers=auth_headers(owner_id))
            created = await client.post(
                "/api/v1/assistant/mcp_servers",
                headers=auth_headers(owner_id),
                json={
                    "name": "资料检索",
                    "description": "给 Hook 调用的个人外部工具",
                    "url": "https://example.com/user-mcp",
                    "headers": {"X-Test": "demo"},
                },
            )
            created_payload = created.json()
            detail = await client.get(
                f"/api/v1/assistant/mcp_servers/{created_payload['id']}",
                headers=auth_headers(owner_id),
            )
            updated = await client.put(
                f"/api/v1/assistant/mcp_servers/{created_payload['id']}",
                headers=auth_headers(owner_id),
                json={
                    "name": "资料检索",
                    "description": "更新后的说明",
                    "enabled": False,
                    "version": created_payload["version"],
                    "transport": created_payload["transport"],
                    "url": "https://example.com/user-mcp/v2",
                    "headers": {"X-Test": "demo-2"},
                    "timeout": 45,
                },
            )
            deleted = await client.delete(
                f"/api/v1/assistant/mcp_servers/{created_payload['id']}",
                headers=auth_headers(owner_id),
            )
            final_list = await client.get("/api/v1/assistant/mcp_servers", headers=auth_headers(owner_id))

        assert initial.status_code == 200
        assert initial.json() == []
        assert created.status_code == 200
        assert created_payload["id"].startswith("mcp.user.")
        assert created_payload["header_count"] == 1
        assert detail.status_code == 200
        assert detail.json()["url"] == "https://example.com/user-mcp"
        assert updated.status_code == 200
        assert updated.json()["enabled"] is False
        assert updated.json()["timeout"] == 45
        assert deleted.status_code == 204
        assert final_list.status_code == 200
        assert final_list.json() == []
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_mcp_api_project_crud(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(
        "EASYSTORY_ASSISTANT_CONFIG_ROOT",
        str(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-project-mcp-api")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
        app = create_app(async_session_factory=async_session_factory)

        async with started_async_client(app) as client:
            initial = await client.get(
                f"/api/v1/assistant/mcp_servers/projects/{project.id}",
                headers=auth_headers(owner.id),
            )
            created = await client.post(
                f"/api/v1/assistant/mcp_servers/projects/{project.id}",
                headers=auth_headers(owner.id),
                json={
                    "name": "项目资料检索",
                    "url": "https://example.com/project-mcp",
                    "headers": {"X-Test": "project"},
                },
            )
            created_payload = created.json()
            detail = await client.get(
                f"/api/v1/assistant/mcp_servers/projects/{project.id}/{created_payload['id']}",
                headers=auth_headers(owner.id),
            )
            updated = await client.put(
                f"/api/v1/assistant/mcp_servers/projects/{project.id}/{created_payload['id']}",
                headers=auth_headers(owner.id),
                json={
                    "name": "项目资料检索",
                    "description": "更新后的项目说明",
                    "enabled": False,
                    "version": created_payload["version"],
                    "transport": created_payload["transport"],
                    "url": "https://example.com/project-mcp/v2",
                    "headers": {"X-Test": "project-2"},
                    "timeout": 45,
                },
            )
            deleted = await client.delete(
                f"/api/v1/assistant/mcp_servers/projects/{project.id}/{created_payload['id']}",
                headers=auth_headers(owner.id),
            )
            final_list = await client.get(
                f"/api/v1/assistant/mcp_servers/projects/{project.id}",
                headers=auth_headers(owner.id),
            )

        assert initial.status_code == 200
        assert initial.json() == []
        assert created.status_code == 200
        assert created_payload["id"].startswith("mcp.project.")
        assert detail.status_code == 200
        assert detail.json()["url"] == "https://example.com/project-mcp"
        assert updated.status_code == 200
        assert updated.json()["enabled"] is False
        assert deleted.status_code == 204
        assert final_list.status_code == 200
        assert final_list.json() == []
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_mcp_api_accepts_explicit_project_override_id(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(
        "EASYSTORY_ASSISTANT_CONFIG_ROOT",
        str(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-project-mcp-api-override")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
        app = create_app(async_session_factory=async_session_factory)

        async with started_async_client(app) as client:
            created = await client.post(
                f"/api/v1/assistant/mcp_servers/projects/{project.id}",
                headers=auth_headers(owner.id),
                json={
                    "id": "mcp.news.lookup",
                    "name": "项目覆盖 MCP",
                    "url": "https://example.com/project-mcp",
                    "headers": {"X-Test": "project"},
                },
            )

        assert created.status_code == 200
        assert created.json()["id"] == "mcp.news.lookup"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
