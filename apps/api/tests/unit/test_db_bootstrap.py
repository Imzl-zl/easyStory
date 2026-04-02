from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect, text

from app.shared.db import resolve_async_database_url
from app.shared.db.bootstrap import (
    create_session_factory,
    is_sqlite_database_url,
    normalize_sync_database_url,
)
from app.shared.runtime.errors import ConfigurationError


def test_resolve_async_database_url_upgrades_sqlite_driver() -> None:
    assert (
        resolve_async_database_url("sqlite:///tmp/easystory.db")
        == "sqlite+aiosqlite:///tmp/easystory.db"
    )


def test_resolve_async_database_url_preserves_existing_async_driver() -> None:
    assert (
        resolve_async_database_url("sqlite+aiosqlite:///tmp/easystory.db")
        == "sqlite+aiosqlite:///tmp/easystory.db"
    )


def test_normalize_sync_database_url_downshifts_async_driver() -> None:
    assert (
        normalize_sync_database_url("sqlite+aiosqlite:///tmp/easystory.db")
        == "sqlite:///tmp/easystory.db"
    )


def test_is_sqlite_database_url_accepts_async_sqlite_driver() -> None:
    assert is_sqlite_database_url("sqlite+aiosqlite:///tmp/easystory.db") is True
    assert is_sqlite_database_url("postgresql+asyncpg://user:pass@localhost/easystory") is False


def test_create_session_factory_reconciles_legacy_model_credentials_table(tmp_path) -> None:
    database_path = tmp_path / "legacy-model-credentials.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    legacy_engine = create_engine(database_url)
    with legacy_engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE model_credentials (
                    id TEXT PRIMARY KEY,
                    owner_type VARCHAR(20) NOT NULL,
                    owner_id TEXT,
                    provider VARCHAR(50) NOT NULL,
                    display_name VARCHAR(100) NOT NULL,
                    encrypted_key TEXT NOT NULL,
                    base_url VARCHAR(500),
                    is_active BOOLEAN NOT NULL,
                    last_verified_at DATETIME,
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO model_credentials (
                    id,
                    owner_type,
                    owner_id,
                    provider,
                    display_name,
                    encrypted_key,
                    base_url,
                    is_active,
                    last_verified_at,
                    created_at,
                    updated_at
                ) VALUES
                    ('cred-openai', 'user', NULL, 'openai', 'OpenAI', 'enc', NULL, 1, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                    ('cred-anthropic', 'user', NULL, 'anthropic', 'Anthropic', 'enc', NULL, 1, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            )
        )
    legacy_engine.dispose()

    session_factory = create_session_factory(database_url)
    session_factory.kw["bind"].dispose()

    reconciled_engine = create_engine(database_url)
    assert "alembic_version" in inspect(reconciled_engine).get_table_names()
    columns = {column["name"] for column in inspect(reconciled_engine).get_columns("model_credentials")}
    assert {
        "api_dialect",
        "context_window_tokens",
        "default_max_output_tokens",
        "default_model",
        "user_agent_override",
        "client_name",
        "client_version",
        "runtime_kind",
    } <= columns

    with reconciled_engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT provider, api_dialect, default_model
                FROM model_credentials
                ORDER BY provider
                """
            )
        ).mappings().all()

    assert rows == [
        {
            "provider": "anthropic",
            "api_dialect": "anthropic_messages",
            "default_model": None,
        },
        {
            "provider": "openai",
            "api_dialect": "openai_chat_completions",
            "default_model": None,
        },
    ]
    reconciled_engine.dispose()


def test_create_session_factory_bootstraps_empty_database_with_alembic(tmp_path) -> None:
    database_path = tmp_path / "bootstrap-empty.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

    session_factory = create_session_factory(database_url)
    session_factory.kw["bind"].dispose()

    initialized_engine = create_engine(database_url)
    try:
        table_names = set(inspect(initialized_engine).get_table_names())
        assert {"users", "projects", "alembic_version"} <= table_names
    finally:
        initialized_engine.dispose()


def test_create_session_factory_fails_fast_on_empty_alembic_version_with_existing_tables(
    tmp_path,
) -> None:
    database_path = tmp_path / "invalid-alembic-state.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(
            text(
                """
                CREATE TABLE model_credentials (
                    id TEXT PRIMARY KEY,
                    owner_type VARCHAR(20) NOT NULL,
                    owner_id TEXT,
                    provider VARCHAR(50) NOT NULL,
                    display_name VARCHAR(100) NOT NULL,
                    encrypted_key TEXT NOT NULL,
                    base_url VARCHAR(500),
                    is_active BOOLEAN NOT NULL,
                    last_verified_at DATETIME,
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )
        )
    engine.dispose()

    with pytest.raises(ConfigurationError, match="迁移状态损坏"):
        create_session_factory(database_url)


def test_create_session_factory_bootstraps_in_memory_database_with_alembic() -> None:
    session_factory = create_session_factory("sqlite:///:memory:")
    engine = session_factory.kw["bind"]

    try:
        table_names = set(inspect(engine).get_table_names())
        assert {"users", "projects", "alembic_version"} <= table_names
        with session_factory() as session:
            assert session.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    finally:
        engine.dispose()
