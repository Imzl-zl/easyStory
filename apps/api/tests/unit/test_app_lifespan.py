from __future__ import annotations

from sqlalchemy import select

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
            templates = session.scalars(select(Template)).all()
            assert templates
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
