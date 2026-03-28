from __future__ import annotations

from app.main import create_app
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.models.helpers import create_user


async def test_assistant_preferences_api_reads_and_updates_user_preferences(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(
        "EASYSTORY_ASSISTANT_CONFIG_ROOT",
        str(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-preferences-api")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        app = create_app(async_session_factory=async_session_factory)

        async with started_async_client(app) as client:
            initial = await client.get(
                "/api/v1/assistant/preferences",
                headers=auth_headers(owner_id),
            )
            updated = await client.put(
                "/api/v1/assistant/preferences",
                headers=auth_headers(owner_id),
                json={
                    "default_provider": "anthropic",
                    "default_model_name": "claude-sonnet-4",
                },
            )
            refreshed = await client.get(
                "/api/v1/assistant/preferences",
                headers=auth_headers(owner_id),
            )

        assert initial.status_code == 200
        assert initial.json() == {
            "default_provider": None,
            "default_model_name": None,
        }
        assert updated.status_code == 200
        assert updated.json() == {
            "default_provider": "anthropic",
            "default_model_name": "claude-sonnet-4",
        }
        assert refreshed.status_code == 200
        assert refreshed.json() == {
            "default_provider": "anthropic",
            "default_model_name": "claude-sonnet-4",
        }
        preferences_file = (
            tmp_path / "assistant-config" / "users" / str(owner_id) / "preferences.yaml"
        )
        assert preferences_file.exists()
        file_text = preferences_file.read_text(encoding="utf-8")
        assert "default_provider: anthropic" in file_text
        assert "default_model_name: claude-sonnet-4" in file_text
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
