from __future__ import annotations

from app.main import create_app
from app.shared.settings import CONFIG_ADMIN_USERNAMES_ENV, clear_settings_cache
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers as _auth_headers
from tests.unit.models.helpers import create_user

CONTROL_PLANE_ADMIN = "template-admin"


def _configure_control_plane_admin(monkeypatch) -> None:
    monkeypatch.setenv(CONFIG_ADMIN_USERNAMES_ENV, CONTROL_PLANE_ADMIN)
    clear_settings_cache()


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


async def test_template_api_supports_custom_template_crud(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    _configure_control_plane_admin(monkeypatch)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="template-api-write")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session, username=CONTROL_PLANE_ADMIN).id

        app = create_app(
            async_session_factory=async_session_factory,
        )
        async with started_async_client(app) as client:
            create_response = await client.post(
                "/api/v1/templates",
                headers=_auth_headers(owner_id),
                json={
                    "name": "自定义模板",
                    "description": "用于 API 回归",
                    "genre": "玄幻",
                    "workflow_id": "workflow.xuanhuan_manual",
                    "guided_questions": [
                        {"question": "主角是谁?", "variable": "protagonist"}
                    ],
                },
            )
            assert create_response.status_code == 201
            detail = create_response.json()
            assert detail["name"] == "自定义模板"
            assert detail["is_builtin"] is False
            assert [node["node_id"] for node in detail["nodes"]] == [
                "outline",
                "opening_plan",
                "chapter_split",
                "chapter_gen",
                "export",
            ]

            template_id = detail["id"]
            update_response = await client.put(
                f"/api/v1/templates/{template_id}",
                headers=_auth_headers(owner_id),
                json={
                    "name": "自定义模板-v2",
                    "description": "更新后的模板",
                    "genre": "仙侠",
                    "workflow_id": "workflow.xuanhuan_manual",
                    "guided_questions": [
                        {"question": "  核心冲突是什么?  ", "variable": " conflict "}
                    ],
                },
            )
            assert update_response.status_code == 200
            updated = update_response.json()
            assert updated["name"] == "自定义模板-v2"
            assert [question["question"] for question in updated["guided_questions"]] == [
                "核心冲突是什么?"
            ]
            assert [question["variable"] for question in updated["guided_questions"]] == [
                "core_conflict"
            ]

            delete_response = await client.delete(
                f"/api/v1/templates/{template_id}",
                headers=_auth_headers(owner_id),
            )
            assert delete_response.status_code == 204

            missing_response = await client.get(
                f"/api/v1/templates/{template_id}",
                headers=_auth_headers(owner_id),
            )
            assert missing_response.status_code == 404
            assert missing_response.json()["code"] == "not_found"
    finally:
        clear_settings_cache()
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_template_api_rejects_builtin_mutation_and_duplicate_names(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    _configure_control_plane_admin(monkeypatch)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="template-api-rules")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session, username=CONTROL_PLANE_ADMIN).id

        app = create_app(
            async_session_factory=async_session_factory,
        )
        async with started_async_client(app) as client:
            list_response = await client.get("/api/v1/templates", headers=_auth_headers(owner_id))
            builtin_template_id = list_response.json()[0]["id"]

            duplicate_response = await client.post(
                "/api/v1/templates",
                headers=_auth_headers(owner_id),
                json={
                    "name": "玄幻小说模板",
                    "workflow_id": "workflow.xuanhuan_manual",
                },
            )
            assert duplicate_response.status_code == 409
            assert duplicate_response.json()["code"] == "conflict"

            builtin_update_response = await client.put(
                f"/api/v1/templates/{builtin_template_id}",
                headers=_auth_headers(owner_id),
                json={
                    "name": "内建模板不能修改",
                    "workflow_id": "workflow.xuanhuan_manual",
                },
            )
            assert builtin_update_response.status_code == 422
            assert builtin_update_response.json()["code"] == "business_rule_error"
    finally:
        clear_settings_cache()
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_template_api_allows_read_but_forbids_write_for_non_admin(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    _configure_control_plane_admin(monkeypatch)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="template-api-non-admin")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session, username="normal-user").id

        app = create_app(
            async_session_factory=async_session_factory,
        )
        async with started_async_client(app) as client:
            list_response = await client.get("/api/v1/templates", headers=_auth_headers(owner_id))
            assert list_response.status_code == 200

            create_response = await client.post(
                "/api/v1/templates",
                headers=_auth_headers(owner_id),
                json={
                    "name": "普通用户模板",
                    "workflow_id": "workflow.xuanhuan_manual",
                },
            )
            assert create_response.status_code == 403
            assert create_response.json()["code"] == "forbidden"
    finally:
        clear_settings_cache()
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
