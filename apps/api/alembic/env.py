from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.modules import model_registry as _model_registry  # noqa: F401
from app.shared.db import Base
from app.shared.db.bootstrap import (
    is_sqlite_database_url,
    normalize_sync_database_url,
    resolve_database_url,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _resolve_alembic_database_url() -> str:
    x_args = context.get_x_argument(as_dictionary=True)
    override_url = x_args.get("database_url")
    if override_url:
        return normalize_sync_database_url(override_url)
    configured_url = config.get_main_option("sqlalchemy.url")
    if configured_url:
        return normalize_sync_database_url(configured_url)
    return normalize_sync_database_url(resolve_database_url())


def run_migrations_offline() -> None:
    database_url = _resolve_alembic_database_url()
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=is_sqlite_database_url(database_url),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    provided_connection = config.attributes.get("connection")
    if provided_connection is not None:
        context.configure(
            connection=provided_connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=is_sqlite_database_url(str(provided_connection.engine.url)),
        )

        with context.begin_transaction():
            context.run_migrations()
        return

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _resolve_alembic_database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=is_sqlite_database_url(str(connection.engine.url)),
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
