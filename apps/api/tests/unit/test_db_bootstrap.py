from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

from app.shared.db import resolve_async_database_url
from app.shared.db.bootstrap import create_session_factory


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
    columns = {column["name"] for column in inspect(reconciled_engine).get_columns("model_credentials")}
    assert {"api_dialect", "default_model"} <= columns

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
