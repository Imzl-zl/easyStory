from __future__ import annotations

from app.main import create_app
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.models.helpers import create_user


async def test_assistant_agent_api_crud(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(
        "EASYSTORY_ASSISTANT_CONFIG_ROOT",
        str(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-agent-api")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        app = create_app(async_session_factory=async_session_factory)

        async with started_async_client(app) as client:
            initial = await client.get("/api/v1/assistant/agents", headers=auth_headers(owner_id))
            created = await client.post(
                "/api/v1/assistant/agents",
                headers=auth_headers(owner_id),
                json={
                    "name": "故事陪跑 Agent",
                    "description": "更像一个长期创作搭子",
                    "enabled": True,
                    "skill_id": "skill.assistant.general_chat",
                    "system_prompt": "先给结论，再帮我拆成下一步。",
                    "default_provider": "anthropic",
                    "default_model_name": "claude-sonnet-4",
                    "default_max_output_tokens": 8192,
                },
            )
            created_payload = created.json()
            agent_file = (
                tmp_path
                / "assistant-config"
                / "users"
                / str(owner_id)
                / "agents"
                / created_payload["id"]
                / "AGENT.md"
            )
            agent_file_text = agent_file.read_text(encoding="utf-8")
            listed = await client.get("/api/v1/assistant/agents", headers=auth_headers(owner_id))
            detail = await client.get(
                f"/api/v1/assistant/agents/{created_payload['id']}",
                headers=auth_headers(owner_id),
            )
            updated = await client.put(
                f"/api/v1/assistant/agents/{created_payload['id']}",
                headers=auth_headers(owner_id),
                json={
                    "name": "故事陪跑 Agent",
                    "description": "更新后的说明",
                    "enabled": False,
                    "skill_id": "skill.assistant.general_chat",
                    "system_prompt": "先给一个方向，再问一个关键问题。",
                },
            )
            deleted = await client.delete(
                f"/api/v1/assistant/agents/{created_payload['id']}",
                headers=auth_headers(owner_id),
            )
            final_list = await client.get("/api/v1/assistant/agents", headers=auth_headers(owner_id))

        assert initial.status_code == 200
        assert initial.json() == []
        assert created.status_code == 200
        assert created_payload["id"].startswith("agent.user.")
        assert created_payload["skill_id"] == "skill.assistant.general_chat"
        assert "故事陪跑 Agent" in agent_file_text
        assert listed.status_code == 200
        assert listed.json()[0]["id"] == created_payload["id"]
        assert detail.status_code == 200
        assert detail.json()["system_prompt"].startswith("先给结论")
        assert updated.status_code == 200
        assert updated.json()["enabled"] is False
        assert updated.json()["description"] == "更新后的说明"
        assert deleted.status_code == 204
        assert final_list.status_code == 200
        assert final_list.json() == []
        assert not agent_file.exists()
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_agent_api_rejects_blank_name_without_writing_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(
        "EASYSTORY_ASSISTANT_CONFIG_ROOT",
        str(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-agent-api-blank-name")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        app = create_app(async_session_factory=async_session_factory)

        async with started_async_client(app) as client:
            response = await client.post(
                "/api/v1/assistant/agents",
                headers=auth_headers(owner_id),
                json={
                    "name": "   ",
                    "skill_id": "skill.assistant.general_chat",
                    "system_prompt": "请先给结论。",
                },
            )

        assert response.status_code == 422
        assert not (tmp_path / "assistant-config" / "users" / str(owner_id) / "agents").exists()
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
