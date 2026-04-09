from __future__ import annotations

from app.main import create_app
from app.modules.credential.models import ModelCredential
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.models.helpers import create_project, create_user


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
                    "default_max_output_tokens": 8192,
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
            "default_max_output_tokens": None,
            "default_reasoning_effort": None,
            "default_thinking_level": None,
            "default_thinking_budget": None,
        }
        assert updated.status_code == 200
        assert updated.json() == {
            "default_provider": "anthropic",
            "default_model_name": "claude-sonnet-4",
            "default_max_output_tokens": 8192,
            "default_reasoning_effort": None,
            "default_thinking_level": None,
            "default_thinking_budget": None,
        }
        assert refreshed.status_code == 200
        assert refreshed.json() == {
            "default_provider": "anthropic",
            "default_model_name": "claude-sonnet-4",
            "default_max_output_tokens": 8192,
            "default_reasoning_effort": None,
            "default_thinking_level": None,
            "default_thinking_budget": None,
        }
        preferences_file = (
            tmp_path / "assistant-config" / "users" / str(owner_id) / "preferences.yaml"
        )
        assert preferences_file.exists()
        file_text = preferences_file.read_text(encoding="utf-8")
        assert "default_provider: anthropic" in file_text
        assert "default_model_name: claude-sonnet-4" in file_text
        assert "default_max_output_tokens: 8192" in file_text
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_preferences_api_reads_and_updates_project_preferences(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(
        "EASYSTORY_ASSISTANT_CONFIG_ROOT",
        str(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-project-preferences-api")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            session.add(
                ModelCredential(
                    owner_type="user",
                    owner_id=owner.id,
                    provider="gemini",
                    api_dialect="gemini_generate_content",
                    display_name="Gemini",
                    encrypted_key="fake-key",
                    default_model="gemini-2.5-flash",
                    is_active=True,
                )
            )
            session.commit()
        app = create_app(async_session_factory=async_session_factory)

        async with started_async_client(app) as client:
            initial = await client.get(
                f"/api/v1/assistant/preferences/projects/{project.id}",
                headers=auth_headers(owner.id),
            )
            updated = await client.put(
                f"/api/v1/assistant/preferences/projects/{project.id}",
                headers=auth_headers(owner.id),
                json={
                    "default_provider": "gemini",
                    "default_model_name": "gemini-2.5-flash",
                    "default_max_output_tokens": 6144,
                    "default_thinking_budget": 0,
                },
            )
            refreshed = await client.get(
                f"/api/v1/assistant/preferences/projects/{project.id}",
                headers=auth_headers(owner.id),
            )

        assert initial.status_code == 200
        assert initial.json() == {
            "default_provider": None,
            "default_model_name": None,
            "default_max_output_tokens": None,
            "default_reasoning_effort": None,
            "default_thinking_level": None,
            "default_thinking_budget": None,
        }
        assert updated.status_code == 200
        assert updated.json() == {
            "default_provider": "gemini",
            "default_model_name": "gemini-2.5-flash",
            "default_max_output_tokens": 6144,
            "default_reasoning_effort": None,
            "default_thinking_level": None,
            "default_thinking_budget": 0,
        }
        assert refreshed.status_code == 200
        assert refreshed.json() == {
            "default_provider": "gemini",
            "default_model_name": "gemini-2.5-flash",
            "default_max_output_tokens": 6144,
            "default_reasoning_effort": None,
            "default_thinking_level": None,
            "default_thinking_budget": 0,
        }
        preferences_file = (
            tmp_path / "assistant-config" / "projects" / str(project.id) / "preferences.yaml"
        )
        assert preferences_file.exists()
        file_text = preferences_file.read_text(encoding="utf-8")
        assert "default_provider: gemini" in file_text
        assert "default_model_name: gemini-2.5-flash" in file_text
        assert "default_max_output_tokens: 6144" in file_text
        assert "default_thinking_budget: 0" in file_text
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_preferences_api_accepts_flexible_openai_reasoning_without_target_resolution(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(
        "EASYSTORY_ASSISTANT_CONFIG_ROOT",
        str(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-preferences-api-invalid-reasoning")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        app = create_app(async_session_factory=async_session_factory)

        async with started_async_client(app) as client:
            response = await client.put(
                "/api/v1/assistant/preferences",
                headers=auth_headers(owner_id),
                json={
                    "default_model_name": "gpt-4.1",
                    "default_reasoning_effort": "minimal",
                },
            )

        assert response.status_code == 200
        assert response.json()["default_reasoning_effort"] == "minimal"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_preferences_api_accepts_reasoning_for_openai_compatible_targets(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(
        "EASYSTORY_ASSISTANT_CONFIG_ROOT",
        str(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(
            tmp_path,
            name="assistant-preferences-api-custom-openai-target",
        )
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            session.add(
                ModelCredential(
                    owner_type="user",
                    owner_id=owner.id,
                    provider="new_api",
                    api_dialect="openai_chat_completions",
                    display_name="兼容 OpenAI",
                    encrypted_key="fake-key",
                    default_model="deepseek-reasoner",
                    is_active=True,
                )
            )
            session.commit()
        app = create_app(async_session_factory=async_session_factory)

        async with started_async_client(app) as client:
            response = await client.put(
                "/api/v1/assistant/preferences",
                headers=auth_headers(owner.id),
                json={
                    "default_provider": "new_api",
                    "default_model_name": "deepseek-reasoner",
                    "default_reasoning_effort": "high",
                },
            )

        assert response.status_code == 200
        assert response.json()["default_reasoning_effort"] == "high"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_preferences_api_accepts_provider_native_reasoning_without_active_credential(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(
        "EASYSTORY_ASSISTANT_CONFIG_ROOT",
        str(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(
            tmp_path,
            name="assistant-preferences-api-missing-credential-target",
        )
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
        app = create_app(async_session_factory=async_session_factory)

        async with started_async_client(app) as client:
            response = await client.put(
                "/api/v1/assistant/preferences",
                headers=auth_headers(owner.id),
                json={
                    "default_provider": "new_api",
                    "default_model_name": "gpt-5.4",
                    "default_reasoning_effort": "high",
                },
            )

        assert response.status_code == 200
        assert response.json()["default_provider"] == "new_api"
        assert response.json()["default_reasoning_effort"] == "high"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_preferences_api_accepts_openai_reasoning_without_active_credential(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(
        "EASYSTORY_ASSISTANT_CONFIG_ROOT",
        str(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(
            tmp_path,
            name="assistant-preferences-api-missing-openai-credential-target",
        )
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
        app = create_app(async_session_factory=async_session_factory)

        async with started_async_client(app) as client:
            response = await client.put(
                "/api/v1/assistant/preferences",
                headers=auth_headers(owner.id),
                json={
                    "default_provider": "openai",
                    "default_model_name": "gpt-5.4",
                    "default_reasoning_effort": "high",
                },
            )

        assert response.status_code == 200
        assert response.json()["default_provider"] == "openai"
        assert response.json()["default_reasoning_effort"] == "high"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_preferences_api_rejects_reasoning_for_resolved_anthropic_target(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(
        "EASYSTORY_ASSISTANT_CONFIG_ROOT",
        str(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(
            tmp_path,
            name="assistant-preferences-api-anthropic-target",
        )
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            session.add(
                ModelCredential(
                    owner_type="user",
                    owner_id=owner.id,
                    provider="anthropic",
                    api_dialect="anthropic_messages",
                    display_name="Anthropic",
                    encrypted_key="fake-key",
                    default_model="claude-sonnet-4",
                    is_active=True,
                )
            )
            session.commit()
        app = create_app(async_session_factory=async_session_factory)

        async with started_async_client(app) as client:
            response = await client.put(
                "/api/v1/assistant/preferences",
                headers=auth_headers(owner.id),
                json={
                    "default_provider": "anthropic",
                    "default_model_name": "gpt-5.4",
                    "default_reasoning_effort": "high",
                },
            )

        assert response.status_code == 422
        assert "default_reasoning_effort is not valid for Anthropic requests" in response.text
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_preferences_api_keeps_project_reasoning_against_inherited_openai_target(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(
        "EASYSTORY_ASSISTANT_CONFIG_ROOT",
        str(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(
            tmp_path,
            name="assistant-project-preferences-api-invalid-inherited-reasoning",
        )
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
            session.add(
                ModelCredential(
                    owner_type="user",
                    owner_id=owner.id,
                    provider="openai",
                    api_dialect="openai_responses",
                    display_name="OpenAI",
                    encrypted_key="fake-key",
                    default_model="gpt-4.1",
                    is_active=True,
                )
            )
            session.commit()
        app = create_app(async_session_factory=async_session_factory)

        async with started_async_client(app) as client:
            user_response = await client.put(
                "/api/v1/assistant/preferences",
                headers=auth_headers(owner.id),
                json={
                    "default_provider": "openai",
                    "default_model_name": "gpt-4.1",
                },
            )
            project_response = await client.put(
                f"/api/v1/assistant/preferences/projects/{project.id}",
                headers=auth_headers(owner.id),
                json={
                    "default_reasoning_effort": "high",
                },
            )

        assert user_response.status_code == 200
        assert project_response.status_code == 200
        assert project_response.json()["default_reasoning_effort"] == "high"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_preferences_api_exposes_legacy_invalid_shape_and_rejects_resave(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv(
        "EASYSTORY_ASSISTANT_CONFIG_ROOT",
        str(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(
            tmp_path,
            name="assistant-preferences-api-legacy-read-compat",
        )
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
        preferences_path = (
            tmp_path / "assistant-config" / "users" / str(owner.id) / "preferences.yaml"
        )
        preferences_path.parent.mkdir(parents=True, exist_ok=True)
        preferences_path.write_text(
            "\n".join(
                [
                    'default_provider: "openai"',
                    'default_model_name: "gpt-5.4"',
                    'default_reasoning_effort: "high"',
                    'default_thinking_level: "low"',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        app = create_app(async_session_factory=async_session_factory)

        async with started_async_client(app) as client:
            initial = await client.get(
                "/api/v1/assistant/preferences",
                headers=auth_headers(owner.id),
            )
            roundtrip = await client.put(
                "/api/v1/assistant/preferences",
                headers=auth_headers(owner.id),
                json=initial.json(),
            )
            refreshed = await client.get(
                "/api/v1/assistant/preferences",
                headers=auth_headers(owner.id),
            )

        expected = {
            "default_provider": "openai",
            "default_model_name": "gpt-5.4",
            "default_max_output_tokens": None,
            "default_reasoning_effort": "high",
            "default_thinking_level": "low",
            "default_thinking_budget": None,
        }
        assert initial.status_code == 200
        assert initial.json() == expected
        assert roundtrip.status_code == 422
        assert (
            "default_reasoning_effort cannot be combined with "
            "default_thinking_level or default_thinking_budget" in roundtrip.text
        )
        assert refreshed.status_code == 200
        assert refreshed.json() == expected
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
