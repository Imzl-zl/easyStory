from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from app.main import create_app
from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.entry.http.router import (
    get_config_registry_query_service,
    get_config_registry_workflow_write_service,
)
from app.modules.config_registry.service import (
    create_config_registry_query_service,
    create_config_registry_workflow_write_service,
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
TARGET_WORKFLOW_ID = "workflow.xuanhuan_manual"


@pytest.fixture(autouse=True)
def _clear_cached_settings() -> None:
    clear_settings_cache()
    yield
    clear_settings_cache()


async def test_config_registry_api_reads_and_updates_workflow_detail(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(CONFIG_ADMIN_USERNAMES_ENV, CONFIG_ADMIN_USERNAME)
    temp_root = _copy_config_root(tmp_path)
    config_loader = ConfigLoader(temp_root)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="config-registry-workflow-api")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session, username=CONFIG_ADMIN_USERNAME).id

        app = create_app(async_session_factory=async_session_factory)
        app.dependency_overrides[get_config_registry_query_service] = lambda: (
            create_config_registry_query_service(config_loader=config_loader)
        )
        app.dependency_overrides[get_config_registry_workflow_write_service] = lambda: (
            create_config_registry_workflow_write_service(config_loader=config_loader)
        )

        async with started_async_client(app) as client:
            detail_response = await client.get(
                f"/api/v1/config/workflows/{TARGET_WORKFLOW_ID}",
                headers=_auth_headers(owner_id),
            )
            assert detail_response.status_code == 200
            detail = detail_response.json()
            assert detail["settings"]["default_fix_skill"] == "skill.fix.xuanhuan"
            assert detail["context_injection"]["default_inject"][0]["inject_type"] == "project_setting"

            payload = {**detail, "name": "玄幻小说手动创作 API 更新"}
            _get_by_id(payload["nodes"], "chapter_gen")["context_injection"] = [
                {
                    "inject_type": "chapter_task",
                    "required": True,
                    "count": None,
                    "analysis_id": None,
                    "inject_fields": [],
                }
            ]
            _get_by_id(payload["nodes"], "export")["formats"] = ["txt", "markdown", "docx"]
            update_response = await client.put(
                f"/api/v1/config/workflows/{TARGET_WORKFLOW_ID}",
                json=payload,
                headers=_auth_headers(owner_id),
            )
            assert update_response.status_code == 200
            updated = update_response.json()
            assert updated["name"] == "玄幻小说手动创作 API 更新"
            chapter_node = _get_by_id(updated["nodes"], "chapter_gen")
            assert chapter_node["context_injection"][0]["inject_type"] == "chapter_task"
            export_node = _get_by_id(updated["nodes"], "export")
            assert export_node["formats"] == ["txt", "markdown", "docx"]

            list_response = await client.get(
                "/api/v1/config/workflows",
                headers=_auth_headers(owner_id),
            )
            assert list_response.status_code == 200
            workflow = _get_by_id(list_response.json(), TARGET_WORKFLOW_ID)
            assert workflow["name"] == "玄幻小说手动创作 API 更新"

        source_text = config_loader.get_source_path(TARGET_WORKFLOW_ID).read_text(encoding="utf-8")
        assert "name: 玄幻小说手动创作 API 更新" in source_text
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_config_registry_api_rejects_mismatched_workflow_id(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(CONFIG_ADMIN_USERNAMES_ENV, CONFIG_ADMIN_USERNAME)
    temp_root = _copy_config_root(tmp_path)
    config_loader = ConfigLoader(temp_root)
    query_service = create_config_registry_query_service(config_loader=config_loader)
    detail = await query_service.get_workflow(TARGET_WORKFLOW_ID)
    payload = detail.model_dump(mode="json")
    payload["id"] = "workflow.other"
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="config-registry-workflow-api-mismatch")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session, username=CONFIG_ADMIN_USERNAME).id

        app = create_app(async_session_factory=async_session_factory)
        app.dependency_overrides[get_config_registry_workflow_write_service] = lambda: (
            create_config_registry_workflow_write_service(config_loader=config_loader)
        )

        async with started_async_client(app) as client:
            response = await client.put(
                f"/api/v1/config/workflows/{TARGET_WORKFLOW_ID}",
                json=payload,
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 422
        assert response.json()["code"] == "business_rule_error"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_config_registry_api_rejects_invalid_workflow_node_type(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(CONFIG_ADMIN_USERNAMES_ENV, CONFIG_ADMIN_USERNAME)
    temp_root = _copy_config_root(tmp_path)
    config_loader = ConfigLoader(temp_root)
    query_service = create_config_registry_query_service(config_loader=config_loader)
    payload = (await query_service.get_workflow(TARGET_WORKFLOW_ID)).model_dump(mode="json")
    _get_by_id(payload["nodes"], "chapter_gen")["node_type"] = "bad-type"
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="config-registry-workflow-api-invalid-node-type")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session, username=CONFIG_ADMIN_USERNAME).id

        app = create_app(async_session_factory=async_session_factory)
        app.dependency_overrides[get_config_registry_workflow_write_service] = lambda: (
            create_config_registry_workflow_write_service(config_loader=config_loader)
        )

        async with started_async_client(app) as client:
            response = await client.put(
                f"/api/v1/config/workflows/{TARGET_WORKFLOW_ID}",
                json=payload,
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 422
        assert "generate" in response.text
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_config_registry_api_rejects_workflow_extra_fields(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(CONFIG_ADMIN_USERNAMES_ENV, CONFIG_ADMIN_USERNAME)
    temp_root = _copy_config_root(tmp_path)
    config_loader = ConfigLoader(temp_root)
    query_service = create_config_registry_query_service(config_loader=config_loader)
    payload = (await query_service.get_workflow(TARGET_WORKFLOW_ID)).model_dump(mode="json")
    payload["unexpected_top"] = True
    _get_by_id(payload["nodes"], "chapter_gen")["unexpected_node"] = True
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="config-registry-workflow-api-extra-fields")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session, username=CONFIG_ADMIN_USERNAME).id

        app = create_app(async_session_factory=async_session_factory)
        app.dependency_overrides[get_config_registry_workflow_write_service] = lambda: (
            create_config_registry_workflow_write_service(config_loader=config_loader)
        )

        async with started_async_client(app) as client:
            response = await client.put(
                f"/api/v1/config/workflows/{TARGET_WORKFLOW_ID}",
                json=payload,
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 422
        assert "extra_forbidden" in response.text
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_config_registry_api_rejects_assistant_only_hook_binding(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(CONFIG_ADMIN_USERNAMES_ENV, CONFIG_ADMIN_USERNAME)
    temp_root = _copy_config_root(tmp_path)
    _write_yaml(
        temp_root / "hooks" / "assistant-only.yaml",
        """
hook:
  id: "hook.assistant_only"
  name: "Assistant Only"
  trigger:
    event: "before_assistant_response"
  action:
    type: "script"
    config:
      module: "app.hooks.builtin"
      function: "auto_save_content"
""",
    )
    config_loader = ConfigLoader(temp_root)
    query_service = create_config_registry_query_service(config_loader=config_loader)
    payload = (await query_service.get_workflow(TARGET_WORKFLOW_ID)).model_dump(mode="json")
    _get_by_id(payload["nodes"], "chapter_gen")["hooks"]["after"].append("hook.assistant_only")
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="config-registry-workflow-api-assistant-hook")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session, username=CONFIG_ADMIN_USERNAME).id

        app = create_app(async_session_factory=async_session_factory)
        app.dependency_overrides[get_config_registry_workflow_write_service] = lambda: (
            create_config_registry_workflow_write_service(config_loader=config_loader)
        )

        async with started_async_client(app) as client:
            response = await client.put(
                f"/api/v1/config/workflows/{TARGET_WORKFLOW_ID}",
                json=payload,
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 422
        assert "not supported on workflow nodes" in response.text
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def _get_by_id(items: list[dict], workflow_id: str) -> dict:
    for item in items:
        if item["id"] == workflow_id:
            return item
    raise AssertionError(f"Workflow item not found: {workflow_id}")


def _copy_config_root(tmp_path: Path) -> Path:
    temp_root = tmp_path / "config"
    shutil.copytree(CONFIG_ROOT, temp_root)
    return temp_root


def _write_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
