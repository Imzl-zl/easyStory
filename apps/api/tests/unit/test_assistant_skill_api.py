from __future__ import annotations

from app.main import create_app
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.models.helpers import create_project, create_user


async def test_assistant_skill_api_crud(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(
        "EASYSTORY_ASSISTANT_CONFIG_ROOT",
        str(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-skill-api")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        app = create_app(async_session_factory=async_session_factory)

        async with started_async_client(app) as client:
            initial = await client.get("/api/v1/assistant/skills", headers=auth_headers(owner_id))
            created = await client.post(
                "/api/v1/assistant/skills",
                headers=auth_headers(owner_id),
                json={
                    "name": "故事方向助手",
                    "description": "帮我先收拢方向",
                    "enabled": True,
                    "content": "请先给我 3 个方向。\n用户输入：{{ user_input }}",
                    "default_provider": "anthropic",
                    "default_model_name": "claude-sonnet-4",
                    "default_max_output_tokens": 8192,
                },
            )
            created_payload = created.json()
            skill_file = (
                tmp_path
                / "assistant-config"
                / "users"
                / str(owner_id)
                / "skills"
                / created_payload["id"]
                / "SKILL.md"
            )
            assert skill_file.exists()
            skill_file_text = skill_file.read_text(encoding="utf-8")
            listed = await client.get("/api/v1/assistant/skills", headers=auth_headers(owner_id))
            detail = await client.get(
                f"/api/v1/assistant/skills/{created_payload['id']}",
                headers=auth_headers(owner_id),
            )
            updated = await client.put(
                f"/api/v1/assistant/skills/{created_payload['id']}",
                headers=auth_headers(owner_id),
                json={
                    "name": "故事方向助手",
                    "description": "更新后的说明",
                    "enabled": False,
                    "content": "先给 2 个方向，再追问一个关键问题。\n用户输入：{{ user_input }}",
                },
            )
            deleted = await client.delete(
                f"/api/v1/assistant/skills/{created_payload['id']}",
                headers=auth_headers(owner_id),
            )
            final_list = await client.get("/api/v1/assistant/skills", headers=auth_headers(owner_id))

        assert initial.status_code == 200
        assert initial.json() == []
        assert created.status_code == 200
        assert created_payload["id"].startswith("skill.user.")
        assert created_payload["name"] == "故事方向助手"
        assert created_payload["default_provider"] == "anthropic"
        assert listed.status_code == 200
        assert listed.json()[0]["id"] == created_payload["id"]
        assert "故事方向助手" in skill_file_text
        assert detail.status_code == 200
        assert detail.json()["content"].startswith("请先给我 3 个方向。")
        assert updated.status_code == 200
        assert updated.json()["enabled"] is False
        assert updated.json()["description"] == "更新后的说明"
        assert deleted.status_code == 204
        assert final_list.status_code == 200
        assert final_list.json() == []

        assert not skill_file.exists()
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_skill_api_rejects_blank_name_without_writing_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(
        "EASYSTORY_ASSISTANT_CONFIG_ROOT",
        str(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-skill-api-blank-name")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        app = create_app(async_session_factory=async_session_factory)

        async with started_async_client(app) as client:
            response = await client.post(
                "/api/v1/assistant/skills",
                headers=auth_headers(owner_id),
                json={
                    "name": "   ",
                    "content": "用户输入：{{ user_input }}",
                },
            )

        assert response.status_code == 422
        assert not (tmp_path / "assistant-config" / "users" / str(owner_id) / "skills").exists()
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_skill_api_project_crud(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(
        "EASYSTORY_ASSISTANT_CONFIG_ROOT",
        str(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-project-skill-api")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
        app = create_app(async_session_factory=async_session_factory)

        async with started_async_client(app) as client:
            initial = await client.get(
                f"/api/v1/assistant/skills/projects/{project.id}",
                headers=auth_headers(owner.id),
            )
            created = await client.post(
                f"/api/v1/assistant/skills/projects/{project.id}",
                headers=auth_headers(owner.id),
                json={
                    "name": "项目专用 Skill",
                    "content": "请优先按项目口径回答。\n用户输入：{{ user_input }}",
                },
            )
            created_payload = created.json()
            detail = await client.get(
                f"/api/v1/assistant/skills/projects/{project.id}/{created_payload['id']}",
                headers=auth_headers(owner.id),
            )
            updated = await client.put(
                f"/api/v1/assistant/skills/projects/{project.id}/{created_payload['id']}",
                headers=auth_headers(owner.id),
                json={
                    "name": "项目专用 Skill",
                    "description": "更新后的项目说明",
                    "enabled": False,
                    "content": "请先确认项目背景，再回答。\n用户输入：{{ user_input }}",
                },
            )
            deleted = await client.delete(
                f"/api/v1/assistant/skills/projects/{project.id}/{created_payload['id']}",
                headers=auth_headers(owner.id),
            )
            final_list = await client.get(
                f"/api/v1/assistant/skills/projects/{project.id}",
                headers=auth_headers(owner.id),
            )

        assert initial.status_code == 200
        assert initial.json() == []
        assert created.status_code == 200
        assert created_payload["id"].startswith("skill.project.")
        assert detail.status_code == 200
        assert detail.json()["name"] == "项目专用 Skill"
        assert updated.status_code == 200
        assert updated.json()["enabled"] is False
        assert deleted.status_code == 204
        assert final_list.status_code == 200
        assert final_list.json() == []
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
