from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from app.main import create_app
from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.entry.http.router import (
    get_config_registry_query_service,
    get_config_registry_skill_write_service,
)
from app.modules.config_registry.service import (
    create_config_registry_query_service,
    create_config_registry_skill_write_service,
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


@pytest.fixture(autouse=True)
def _clear_cached_settings() -> None:
    clear_settings_cache()
    yield
    clear_settings_cache()


async def test_config_registry_api_lists_read_only_config_summaries(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(CONFIG_ADMIN_USERNAMES_ENV, CONFIG_ADMIN_USERNAME)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="config-registry-api")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session, username=CONFIG_ADMIN_USERNAME).id

        app = create_app(async_session_factory=async_session_factory)
        async with started_async_client(app) as client:
            skills_response = await client.get(
                "/api/v1/config/skills",
                headers=_auth_headers(owner_id),
            )
            assert skills_response.status_code == 200
            skill = _get_by_id(skills_response.json(), "skill.chapter.xuanhuan")
            assert skill["category"] == "chapter"
            assert skill["model"]["provider"] == "anthropic"
            assert "prompt" not in skill

            agents_response = await client.get(
                "/api/v1/config/agents",
                headers=_auth_headers(owner_id),
            )
            assert agents_response.status_code == 200
            agent = _get_by_id(agents_response.json(), "agent.style_checker")
            assert agent["agent_type"] == "reviewer"
            assert agent["skill_ids"] == ["skill.review.style"]
            assert "system_prompt" not in agent

            hooks_response = await client.get(
                "/api/v1/config/hooks",
                headers=_auth_headers(owner_id),
            )
            assert hooks_response.status_code == 200
            hook = _get_by_id(hooks_response.json(), "hook.auto_save")
            assert hook["trigger_event"] == "after_generate"
            assert hook["action_type"] == "script"

            workflows_response = await client.get(
                "/api/v1/config/workflows",
                headers=_auth_headers(owner_id),
            )
            assert workflows_response.status_code == 200
            workflow = _get_by_id(workflows_response.json(), "workflow.xuanhuan_manual")
            assert workflow["default_fix_skill"] == "skill.fix.xuanhuan"
            assert workflow["default_inject_types"] == ["project_setting", "outline"]
            assert workflow["node_count"] == 5
            chapter_node = _get_by_id(workflow["nodes"], "chapter_gen")
            assert chapter_node["loop_enabled"] is True
            assert chapter_node["reviewer_ids"] == ["agent.style_checker"]
            assert chapter_node["hook_ids"] == ["hook.auto_save"]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_config_registry_api_reads_and_updates_skill_detail(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(CONFIG_ADMIN_USERNAMES_ENV, CONFIG_ADMIN_USERNAME)
    temp_root = _copy_config_root(tmp_path)
    config_loader = ConfigLoader(temp_root)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="config-registry-api-write")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session, username=CONFIG_ADMIN_USERNAME).id

        app = create_app(async_session_factory=async_session_factory)
        app.dependency_overrides[get_config_registry_query_service] = lambda: (
            create_config_registry_query_service(config_loader=config_loader)
        )
        app.dependency_overrides[get_config_registry_skill_write_service] = lambda: (
            create_config_registry_skill_write_service(config_loader=config_loader)
        )

        async with started_async_client(app) as client:
            detail_response = await client.get(
                "/api/v1/config/skills/skill.review.style",
                headers=_auth_headers(owner_id),
            )
            assert detail_response.status_code == 200
            detail = detail_response.json()
            assert detail["prompt"].startswith("你需要检查以下内容")
            assert detail["variables"]["content"]["type"] == "string"

            payload = {
                **detail,
                "name": "文风审核 API 更新",
                "prompt": "你是一名审核编辑。\n\n请检查正文：\n{{ content }}",
            }
            update_response = await client.put(
                "/api/v1/config/skills/skill.review.style",
                json=payload,
                headers=_auth_headers(owner_id),
            )
            assert update_response.status_code == 200
            updated = update_response.json()
            assert updated["name"] == "文风审核 API 更新"
            assert updated["prompt"].endswith("{{ content }}")

            list_response = await client.get(
                "/api/v1/config/skills",
                headers=_auth_headers(owner_id),
            )
            assert list_response.status_code == 200
            skill = _get_by_id(list_response.json(), "skill.review.style")
            assert skill["name"] == "文风审核 API 更新"

        source_text = config_loader.get_source_path("skill.review.style").read_text(encoding="utf-8")
        assert "name: 文风审核 API 更新" in source_text
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_config_registry_api_rejects_mismatched_skill_id(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(CONFIG_ADMIN_USERNAMES_ENV, CONFIG_ADMIN_USERNAME)
    temp_root = _copy_config_root(tmp_path)
    config_loader = ConfigLoader(temp_root)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="config-registry-api-mismatch")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session, username=CONFIG_ADMIN_USERNAME).id

        app = create_app(async_session_factory=async_session_factory)
        app.dependency_overrides[get_config_registry_skill_write_service] = lambda: (
            create_config_registry_skill_write_service(config_loader=config_loader)
        )

        async with started_async_client(app) as client:
            response = await client.put(
                "/api/v1/config/skills/skill.review.style",
                json={
                    "id": "skill.other",
                    "name": "Bad",
                    "version": "1.0.0",
                    "description": None,
                    "category": "review",
                    "author": None,
                    "tags": [],
                    "prompt": "{{ content }}",
                    "variables": {},
                    "inputs": {"content": {"type": "string", "required": True}},
                    "outputs": {},
                    "model": None,
                },
                headers=_auth_headers(owner_id),
            )

        assert response.status_code == 422
        assert response.json()["code"] == "business_rule_error"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_config_registry_api_requires_authentication(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    _session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="config-registry-api-auth")
    )

    try:
        app = create_app(async_session_factory=async_session_factory)
        async with started_async_client(app) as client:
            response = await client.get("/api/v1/config/skills")
            assert response.status_code == 401
            assert response.json()["code"] == "unauthorized"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_config_registry_api_rejects_non_admin_user(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(CONFIG_ADMIN_USERNAMES_ENV, CONFIG_ADMIN_USERNAME)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="config-registry-api-forbidden")
    )

    try:
        with session_factory() as session:
            user_id = create_user(session, username="plain-user").id

        app = create_app(async_session_factory=async_session_factory)
        async with started_async_client(app) as client:
            response = await client.get(
                "/api/v1/config/skills",
                headers=_auth_headers(user_id),
            )
            assert response.status_code == 403
            assert response.json()["code"] == "forbidden"
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
