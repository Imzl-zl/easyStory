from __future__ import annotations

from sqlalchemy import create_engine, inspect, select, text

from app.main import create_app
from app.modules.template.models import Template
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
)

TEST_JWT_SECRET = "test-jwt-secret"


async def test_app_lifespan_runs_startup_template_sync(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="app-lifespan")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        async with app.router.lifespan_context(app):
            pass
        with session_factory() as session:
            assert session.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            templates = session.scalars(select(Template)).all()
            assert templates
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_app_lifespan_bootstraps_owned_database_with_alembic(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    database_path = tmp_path / "owned-lifespan.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    app = create_app(database_url=database_url)
    async_engine = app.state.async_session_factory.kw["bind"]

    try:
        async with app.router.lifespan_context(app):
            engine = create_engine(database_url)
            try:
                table_names = set(inspect(engine).get_table_names())
                assert {"templates", "alembic_version"} <= table_names
                with engine.connect() as connection:
                    assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            finally:
                engine.dispose()
    finally:
        await async_engine.dispose()
