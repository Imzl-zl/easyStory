from __future__ import annotations

from app.main import create_app
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.models.helpers import create_user


async def test_assistant_hook_api_crud(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(
        "EASYSTORY_ASSISTANT_CONFIG_ROOT",
        str(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-hook-api")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        app = create_app(async_session_factory=async_session_factory)

        async with started_async_client(app) as client:
            initial = await client.get("/api/v1/assistant/hooks", headers=auth_headers(owner_id))
            created = await client.post(
                "/api/v1/assistant/hooks",
                headers=auth_headers(owner_id),
                json={
                    "name": "回复后自动整理",
                    "description": "把主回复再收成一句话",
                    "enabled": True,
                    "event": "after_assistant_response",
                    "action": {
                        "action_type": "agent",
                        "agent_id": "agent.general_assistant",
                    },
                },
            )
            created_payload = created.json()
            hook_file = (
                tmp_path
                / "assistant-config"
                / "users"
                / str(owner_id)
                / "hooks"
                / created_payload["id"]
                / "HOOK.yaml"
            )
            hook_file_text = hook_file.read_text(encoding="utf-8")
            listed = await client.get("/api/v1/assistant/hooks", headers=auth_headers(owner_id))
            detail = await client.get(
                f"/api/v1/assistant/hooks/{created_payload['id']}",
                headers=auth_headers(owner_id),
            )
            updated = await client.put(
                f"/api/v1/assistant/hooks/{created_payload['id']}",
                headers=auth_headers(owner_id),
                json={
                    "name": "回复前自动整理",
                    "description": "更新后的说明",
                    "enabled": False,
                    "event": "before_assistant_response",
                    "action": {
                        "action_type": "agent",
                        "agent_id": "agent.general_assistant",
                    },
                },
            )
            deleted = await client.delete(
                f"/api/v1/assistant/hooks/{created_payload['id']}",
                headers=auth_headers(owner_id),
            )
            final_list = await client.get("/api/v1/assistant/hooks", headers=auth_headers(owner_id))

        assert initial.status_code == 200
        assert initial.json() == []
        assert created.status_code == 200
        assert created_payload["id"].startswith("hook.user.")
        assert created_payload["action"]["action_type"] == "agent"
        assert created_payload["action"]["agent_id"] == "agent.general_assistant"
        assert "after_assistant_response" in hook_file_text
        assert listed.status_code == 200
        assert listed.json()[0]["id"] == created_payload["id"]
        assert detail.status_code == 200
        assert detail.json()["event"] == "after_assistant_response"
        assert updated.status_code == 200
        assert updated.json()["enabled"] is False
        assert updated.json()["event"] == "before_assistant_response"
        assert deleted.status_code == 204
        assert final_list.status_code == 200
        assert final_list.json() == []
        assert not hook_file.exists()
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_hook_api_rejects_blank_name_without_writing_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(
        "EASYSTORY_ASSISTANT_CONFIG_ROOT",
        str(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-hook-api-blank-name")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        app = create_app(async_session_factory=async_session_factory)

        async with started_async_client(app) as client:
            response = await client.post(
                "/api/v1/assistant/hooks",
                headers=auth_headers(owner_id),
                json={
                    "name": "   ",
                    "event": "after_assistant_response",
                    "action": {
                        "action_type": "agent",
                        "agent_id": "agent.general_assistant",
                    },
                },
            )

        assert response.status_code == 422
        assert not (tmp_path / "assistant-config" / "users" / str(owner_id) / "hooks").exists()
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
