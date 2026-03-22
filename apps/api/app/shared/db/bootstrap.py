from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.shared.settings import get_settings

from .base import Base

DEFAULT_DB_DIR = ".runtime"
DEFAULT_DB_NAME = "easystory.db"
MODEL_CREDENTIALS_TABLE = "model_credentials"
API_DIALECT_COLUMN = "api_dialect"
DEFAULT_MODEL_COLUMN = "default_model"
OPENAI_CHAT_DIALECT = "openai_chat_completions"
ANTHROPIC_MESSAGES_DIALECT = "anthropic_messages"
ANTHROPIC_PROVIDER = "anthropic"


def create_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    engine = create_database_engine(database_url)
    with engine.begin() as connection:
        _initialize_database(connection)
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def create_async_session_factory(database_url: str | None = None) -> async_sessionmaker[AsyncSession]:
    engine = create_async_database_engine(database_url)
    return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


def create_database_engine(database_url: str | None = None) -> Engine:
    resolved_url = resolve_database_url(database_url)
    return create_engine(resolved_url, **_engine_kwargs(resolved_url))


def create_async_database_engine(database_url: str | None = None) -> AsyncEngine:
    resolved_url = resolve_async_database_url(database_url)
    return create_async_engine(resolved_url, **_async_engine_kwargs(resolved_url))


async def initialize_async_database(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(_initialize_database)


def resolve_database_url(database_url: str | None = None) -> str:
    if database_url:
        return database_url
    settings_database_url = get_settings().database_url
    if settings_database_url:
        return settings_database_url
    database_path = _default_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{database_path.as_posix()}"


def _default_database_path() -> Path:
    api_root = Path(__file__).resolve().parents[3]
    return api_root / DEFAULT_DB_DIR / DEFAULT_DB_NAME


def resolve_async_database_url(database_url: str | None = None) -> str:
    resolved_url = resolve_database_url(database_url)
    if resolved_url.startswith("sqlite+aiosqlite://"):
        return resolved_url
    if resolved_url.startswith("sqlite://"):
        return resolved_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    if resolved_url.startswith("postgresql+asyncpg://"):
        return resolved_url
    if resolved_url.startswith("postgresql://"):
        return resolved_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return resolved_url


def _engine_kwargs(database_url: str) -> dict:
    if not database_url.startswith("sqlite"):
        return {}
    kwargs: dict[str, object] = {"connect_args": {"check_same_thread": False}}
    if _is_memory_sqlite(database_url):
        kwargs["poolclass"] = StaticPool
    return kwargs


def _async_engine_kwargs(database_url: str) -> dict:
    if not database_url.startswith("sqlite+aiosqlite"):
        return {}
    if _is_memory_sqlite(database_url):
        return {"poolclass": StaticPool}
    return {}


def _is_memory_sqlite(database_url: str) -> bool:
    return database_url in {"sqlite://", "sqlite:///:memory:"} or ":memory:" in database_url


def _initialize_database(connection: Connection) -> None:
    Base.metadata.create_all(connection)
    _reconcile_model_credentials_schema(connection)


def _reconcile_model_credentials_schema(connection: Connection) -> None:
    inspector = inspect(connection)
    if MODEL_CREDENTIALS_TABLE not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns(MODEL_CREDENTIALS_TABLE)}
    _add_missing_model_credential_columns(connection, columns)
    _backfill_model_credential_api_dialect(connection)


def _add_missing_model_credential_columns(
    connection: Connection,
    columns: set[str],
) -> None:
    if API_DIALECT_COLUMN not in columns:
        connection.execute(
            text(f"ALTER TABLE {MODEL_CREDENTIALS_TABLE} ADD COLUMN {API_DIALECT_COLUMN} VARCHAR(50)")
        )
        columns.add(API_DIALECT_COLUMN)
    if DEFAULT_MODEL_COLUMN not in columns:
        connection.execute(
            text(
                f"ALTER TABLE {MODEL_CREDENTIALS_TABLE} "
                f"ADD COLUMN {DEFAULT_MODEL_COLUMN} VARCHAR(100)"
            )
        )
        columns.add(DEFAULT_MODEL_COLUMN)


def _backfill_model_credential_api_dialect(connection: Connection) -> None:
    connection.execute(
        text(
            f"""
            UPDATE {MODEL_CREDENTIALS_TABLE}
            SET {API_DIALECT_COLUMN} = CASE
                WHEN lower(provider) = :anthropic_provider THEN :anthropic_dialect
                ELSE :default_dialect
            END
            WHERE {API_DIALECT_COLUMN} IS NULL OR trim({API_DIALECT_COLUMN}) = ''
            """
        ),
        {
            "anthropic_provider": ANTHROPIC_PROVIDER,
            "anthropic_dialect": ANTHROPIC_MESSAGES_DIALECT,
            "default_dialect": OPENAI_CHAT_DIALECT,
        },
    )
