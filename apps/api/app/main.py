from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from app.entry.http.cors import register_cors
from app.entry.http.error_handlers import register_error_handlers
from app.entry.http.router import api_router
from app.modules import model_registry as _model_registry  # noqa: F401
from app.modules.template.service import create_builtin_template_sync_service
from app.shared.db import AsyncSessionFactory, create_async_session_factory, initialize_async_database
from app.shared.settings import validate_startup_settings


async def _run_startup_tasks(app: FastAPI) -> None:
    validate_startup_settings()
    if app.state.owns_async_session_factory:
        await initialize_async_database(_get_async_engine(app.state.async_session_factory))
    async with app.state.async_session_factory() as db:
        await create_builtin_template_sync_service().sync_builtin_templates(db)


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    await _run_startup_tasks(app)
    yield


def _get_async_engine(async_session_factory: AsyncSessionFactory) -> AsyncEngine:
    bind = async_session_factory.kw.get("bind")
    if not isinstance(bind, AsyncEngine):
        raise RuntimeError("Async database engine is not configured")
    return bind


def create_app(
    *,
    async_session_factory: AsyncSessionFactory | None = None,
    database_url: str | None = None,
) -> FastAPI:
    owns_async_session_factory = async_session_factory is None
    resolved_async_session_factory = async_session_factory or create_async_session_factory(database_url)
    app = FastAPI(title="easyStory API", version="0.1.0", lifespan=app_lifespan)
    app.state.owns_async_session_factory = owns_async_session_factory
    app.state.async_session_factory = resolved_async_session_factory
    register_error_handlers(app)
    register_cors(app)
    app.include_router(api_router)

    return app


app = create_app()
