from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection, Engine, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.shared.settings import get_settings
from app.shared.runtime.errors import ConfigurationError

from .base import Base

DEFAULT_DB_DIR = ".runtime"
DEFAULT_DB_NAME = "easystory.db"
ALEMBIC_CONFIG_FILENAME = "alembic.ini"
ALEMBIC_DIRNAME = "alembic"
ALEMBIC_HEAD_TARGET = "head"
ALEMBIC_VERSION_TABLE = "alembic_version"
MODEL_CREDENTIALS_TABLE = "model_credentials"
API_DIALECT_COLUMN = "api_dialect"
DEFAULT_MODEL_COLUMN = "default_model"
CONTEXT_WINDOW_TOKENS_COLUMN = "context_window_tokens"
DEFAULT_MAX_OUTPUT_TOKENS_COLUMN = "default_max_output_tokens"
OPENAI_CHAT_DIALECT = "openai_chat_completions"
ANTHROPIC_MESSAGES_DIALECT = "anthropic_messages"
ANTHROPIC_PROVIDER = "anthropic"
SQLITE_ASYNC_DRIVER = "sqlite+aiosqlite"
SQLITE_DRIVER = "sqlite"
POSTGRES_ASYNC_DRIVER = "postgresql+asyncpg"
POSTGRES_DRIVER = "postgresql"
LOCAL_SQLITE_RESET_HINT = (
    "如果这是可丢弃的本地 SQLite 开发库，请先备份后删除或重命名数据库文件，再重新启动后端。"
)


def create_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    resolved_url = resolve_database_url(database_url)
    engine = create_database_engine(resolved_url)
    try:
        with engine.connect() as connection:
            _initialize_database_connection(connection)
    except Exception:
        engine.dispose()
        raise
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def create_async_session_factory(database_url: str | None = None) -> async_sessionmaker[AsyncSession]:
    engine = create_async_database_engine(database_url)
    return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


def create_database_engine(database_url: str | None = None) -> Engine:
    resolved_url = normalize_sync_database_url(resolve_database_url(database_url))
    return create_engine(resolved_url, **_engine_kwargs(resolved_url))


def create_async_database_engine(database_url: str | None = None) -> AsyncEngine:
    resolved_url = resolve_async_database_url(database_url)
    return create_async_engine(resolved_url, **_async_engine_kwargs(resolved_url))


def initialize_database(database_url: str | None = None) -> None:
    resolved_url = normalize_sync_database_url(resolve_database_url(database_url))
    engine = create_database_engine(resolved_url)
    try:
        with engine.connect() as connection:
            _initialize_database_connection(connection)
    finally:
        engine.dispose()


async def initialize_async_database(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        await connection.run_sync(_initialize_database_connection)


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
    if resolved_url.startswith(f"{SQLITE_ASYNC_DRIVER}://"):
        return resolved_url
    if resolved_url.startswith(f"{SQLITE_DRIVER}://"):
        return resolved_url.replace(f"{SQLITE_DRIVER}://", f"{SQLITE_ASYNC_DRIVER}://", 1)
    if resolved_url.startswith(f"{POSTGRES_ASYNC_DRIVER}://"):
        return resolved_url
    if resolved_url.startswith(f"{POSTGRES_DRIVER}://"):
        return resolved_url.replace(f"{POSTGRES_DRIVER}://", f"{POSTGRES_ASYNC_DRIVER}://", 1)
    return resolved_url


def normalize_sync_database_url(database_url: str) -> str:
    url = make_url(database_url)
    if url.drivername == SQLITE_ASYNC_DRIVER:
        return url.set(drivername=SQLITE_DRIVER).render_as_string(hide_password=False)
    if url.drivername == POSTGRES_ASYNC_DRIVER:
        return url.set(drivername=POSTGRES_DRIVER).render_as_string(hide_password=False)
    return url.render_as_string(hide_password=False)


def is_sqlite_database_url(database_url: str) -> bool:
    return make_url(normalize_sync_database_url(database_url)).drivername == SQLITE_DRIVER


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


def _initialize_database_connection(connection: Connection) -> None:
    database_url = _render_connection_database_url(connection)
    table_names = _get_table_names(connection)
    _validate_alembic_version_state(connection, table_names, database_url=database_url)
    requires_legacy_bootstrap = _requires_legacy_bootstrap(table_names)
    _rollback_if_needed(connection)
    if requires_legacy_bootstrap:
        _bootstrap_legacy_database(connection)
        _commit_if_needed(connection)
        _stamp_database_head(database_url, connection)
        _commit_if_needed(connection)
        return
    _upgrade_database_schema(database_url, connection)
    _reconcile_database_schema(connection)
    _commit_if_needed(connection)


def _render_connection_database_url(connection: Connection) -> str:
    return connection.engine.url.render_as_string(hide_password=False)


def _rollback_if_needed(connection: Connection) -> None:
    if connection.in_transaction():
        connection.rollback()


def _commit_if_needed(connection: Connection) -> None:
    if connection.in_transaction():
        connection.commit()


def _get_table_names(connection: Connection) -> set[str]:
    return set(inspect(connection).get_table_names())


def _requires_legacy_bootstrap(table_names: set[str]) -> bool:
    return ALEMBIC_VERSION_TABLE not in table_names and bool(table_names)


def _validate_alembic_version_state(
    connection: Connection,
    table_names: set[str],
    *,
    database_url: str,
) -> None:
    if ALEMBIC_VERSION_TABLE not in table_names:
        return
    if _has_alembic_revision_rows(connection):
        return
    if table_names == {ALEMBIC_VERSION_TABLE}:
        return
    raise ConfigurationError(_build_invalid_alembic_state_message(database_url))


def _has_alembic_revision_rows(connection: Connection) -> bool:
    rows = connection.execute(
        text(f"SELECT version_num FROM {ALEMBIC_VERSION_TABLE} LIMIT 1")
    ).fetchall()
    return bool(rows)


def _build_invalid_alembic_state_message(database_url: str) -> str:
    return (
        f"检测到数据库迁移状态损坏: {database_url} 中的 {ALEMBIC_VERSION_TABLE} 表已存在，"
        "但没有任何 revision 记录，同时库里已经存在业务表。当前状态无法安全自动修复。"
        f"{LOCAL_SQLITE_RESET_HINT}"
    )


def _bootstrap_legacy_database(connection: Connection) -> None:
    Base.metadata.create_all(connection)
    _reconcile_model_credentials_schema(connection)


def _reconcile_database_schema(connection: Connection) -> None:
    _reconcile_model_credentials_schema(connection)


def _upgrade_database_schema(database_url: str, connection: Connection | None = None) -> None:
    from alembic import command

    command.upgrade(_build_alembic_config(database_url, connection), ALEMBIC_HEAD_TARGET)


def _stamp_database_head(database_url: str, connection: Connection | None = None) -> None:
    from alembic import command

    command.stamp(_build_alembic_config(database_url, connection), ALEMBIC_HEAD_TARGET)


def _build_alembic_config(
    database_url: str,
    connection: Connection | None = None,
):
    from alembic.config import Config

    api_root = Path(__file__).resolve().parents[3]
    config = Config(str(api_root / ALEMBIC_CONFIG_FILENAME))
    config.set_main_option("script_location", str(api_root / ALEMBIC_DIRNAME))
    config.set_main_option("sqlalchemy.url", database_url)
    if connection is not None:
        config.attributes["connection"] = connection
    return config


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
    if CONTEXT_WINDOW_TOKENS_COLUMN not in columns:
        connection.execute(
            text(
                f"ALTER TABLE {MODEL_CREDENTIALS_TABLE} "
                f"ADD COLUMN {CONTEXT_WINDOW_TOKENS_COLUMN} INTEGER"
            )
        )
        columns.add(CONTEXT_WINDOW_TOKENS_COLUMN)
    if DEFAULT_MAX_OUTPUT_TOKENS_COLUMN not in columns:
        connection.execute(
            text(
                f"ALTER TABLE {MODEL_CREDENTIALS_TABLE} "
                f"ADD COLUMN {DEFAULT_MAX_OUTPUT_TOKENS_COLUMN} INTEGER"
            )
        )
        columns.add(DEFAULT_MAX_OUTPUT_TOKENS_COLUMN)


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
