from __future__ import annotations

from app.main import create_app
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers
from tests.unit.async_api_support import build_sqlite_session_factories, cleanup_sqlite_session_factories, started_async_client
from tests.unit.models.helpers import create_project, create_user


async def test_assistant_rule_api_reads_and_updates_user_rules(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(
        "EASYSTORY_ASSISTANT_CONFIG_ROOT",
        str(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-rule-user-api")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        app = create_app(async_session_factory=async_session_factory)

        async with started_async_client(app) as client:
            initial = await client.get(
                "/api/v1/assistant/rules/me",
                headers=auth_headers(owner_id),
            )
            updated = await client.put(
                "/api/v1/assistant/rules/me",
                headers=auth_headers(owner_id),
                json={"enabled": True, "content": "默认先给结论。"},
            )
            refreshed = await client.get(
                "/api/v1/assistant/rules/me",
                headers=auth_headers(owner_id),
            )

        assert initial.status_code == 200
        assert initial.json() == {
            "scope": "user",
            "enabled": False,
            "content": "",
            "updated_at": None,
        }
        assert updated.status_code == 200
        assert updated.json()["enabled"] is True
        assert updated.json()["content"] == "默认先给结论。"
        assert refreshed.status_code == 200
        assert refreshed.json()["content"] == "默认先给结论。"
        rule_file = tmp_path / "assistant-config" / "users" / str(owner_id) / "AGENTS.md"
        assert rule_file.exists()
        assert "默认先给结论。" in rule_file.read_text(encoding="utf-8")
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_rule_api_reads_and_updates_project_rules(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(
        "EASYSTORY_ASSISTANT_CONFIG_ROOT",
        str(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-rule-project-api")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
        app = create_app(async_session_factory=async_session_factory)

        async with started_async_client(app) as client:
            initial = await client.get(
                f"/api/v1/assistant/rules/projects/{project.id}",
                headers=auth_headers(owner.id),
            )
            updated = await client.put(
                f"/api/v1/assistant/rules/projects/{project.id}",
                headers=auth_headers(owner.id),
                json={"enabled": True, "content": "这个项目统一写成古风口吻。"},
            )
            refreshed = await client.get(
                f"/api/v1/assistant/rules/projects/{project.id}",
                headers=auth_headers(owner.id),
            )

        assert initial.status_code == 200
        assert initial.json()["scope"] == "project"
        assert initial.json()["content"] == ""
        assert updated.status_code == 200
        assert updated.json()["enabled"] is True
        assert updated.json()["content"] == "这个项目统一写成古风口吻。"
        assert refreshed.status_code == 200
        assert refreshed.json()["content"] == "这个项目统一写成古风口吻。"
        rule_file = tmp_path / "assistant-config" / "projects" / str(project.id) / "AGENTS.md"
        assert rule_file.exists()
        assert "这个项目统一写成古风口吻。" in rule_file.read_text(encoding="utf-8")
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
