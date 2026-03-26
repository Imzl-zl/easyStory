from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from app.main import create_app
from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.entry.http.router import (
    get_config_registry_mcp_write_service,
    get_config_registry_query_service,
)
from app.modules.config_registry.service import (
    create_config_registry_mcp_write_service,
    create_config_registry_query_service,
)
from app.shared.settings import CONFIG_ADMIN_USERNAMES_ENV, clear_settings_cache
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers as _auth_headers
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.models.helpers import create_user

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CONFIG_ROOT = PROJECT_ROOT / "config"
CONFIG_ADMIN_USERNAME = "config-admin"
TARGET_SERVER_ID = "mcp.example.streamable_http"


@pytest.fixture(autouse=True)
def _clear_cached_settings() -> None:
    clear_settings_cache()
    yield
    clear_settings_cache()


async def test_config_registry_api_reads_and_updates_mcp_server_detail(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(CONFIG_ADMIN_USERNAMES_ENV, CONFIG_ADMIN_USERNAME)
    temp_root = _copy_config_root(tmp_path)
    config_loader = ConfigLoader(temp_root)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="config-registry-mcp-api")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session, username=CONFIG_ADMIN_USERNAME).id

        app = create_app(async_session_factory=async_session_factory)
        app.dependency_overrides[get_config_registry_query_service] = lambda: (
            create_config_registry_query_service(config_loader=config_loader)
        )
        app.dependency_overrides[get_config_registry_mcp_write_service] = lambda: (
            create_config_registry_mcp_write_service(config_loader=config_loader)
        )

        async with started_async_client(app) as client:
            list_response = await client.get(
                "/api/v1/config/mcp_servers",
                headers=_auth_headers(owner_id),
            )
            assert list_response.status_code == 200
            summary = _get_by_id(list_response.json(), TARGET_SERVER_ID)
            assert summary["transport"] == "streamable_http"
            assert summary["enabled"] is False
            assert summary["header_count"] == 0

            detail_response = await client.get(
                f"/api/v1/config/mcp_servers/{TARGET_SERVER_ID}",
                headers=_auth_headers(owner_id),
            )
            assert detail_response.status_code == 200
            detail = detail_response.json()
            assert detail["url"] == "https://example.com/mcp"
            assert detail["headers"] == {}

            payload = {
                **detail,
                "name": "示例新闻 MCP",
                "headers": {"X-Feature": "news"},
                "timeout": 45,
                "enabled": True,
            }
            update_response = await client.put(
                f"/api/v1/config/mcp_servers/{TARGET_SERVER_ID}",
                json=payload,
                headers=_auth_headers(owner_id),
            )
            assert update_response.status_code == 200
            updated = update_response.json()
            assert updated["name"] == "示例新闻 MCP"
            assert updated["headers"] == {"X-Feature": "news"}
            assert updated["timeout"] == 45
            assert updated["enabled"] is True

        source_text = config_loader.get_source_path(TARGET_SERVER_ID).read_text(encoding="utf-8")
        assert "name: 示例新闻 MCP" in source_text
        assert "X-Feature: news" in source_text
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_config_registry_api_rejects_mismatched_mcp_server_id(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(CONFIG_ADMIN_USERNAMES_ENV, CONFIG_ADMIN_USERNAME)
    temp_root = _copy_config_root(tmp_path)
    config_loader = ConfigLoader(temp_root)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="config-registry-mcp-api-mismatch")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session, username=CONFIG_ADMIN_USERNAME).id

        app = create_app(async_session_factory=async_session_factory)
        app.dependency_overrides[get_config_registry_mcp_write_service] = lambda: (
            create_config_registry_mcp_write_service(config_loader=config_loader)
        )

        async with started_async_client(app) as client:
            response = await client.put(
                f"/api/v1/config/mcp_servers/{TARGET_SERVER_ID}",
                json={
                    "id": "mcp.other",
                    "name": "Bad",
                    "version": "1.0.0",
                    "description": None,
                    "author": None,
                    "transport": "streamable_http",
                    "url": "https://example.com/other",
                    "headers": {},
                    "timeout": 30,
                    "enabled": True,
                },
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 422
        assert response.json()["code"] == "business_rule_error"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def _get_by_id(items: list[dict], config_id: str) -> dict:
    for item in items:
        if item["id"] == config_id:
            return item
    raise AssertionError(f"Config item not found: {config_id}")


def _copy_config_root(tmp_path: Path) -> Path:
    temp_root = tmp_path / "config"
    shutil.copytree(CONFIG_ROOT, temp_root)
    return temp_root
