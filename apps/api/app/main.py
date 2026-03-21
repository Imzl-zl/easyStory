from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.entry.http.cors import register_cors
from app.entry.http.error_handlers import register_error_handlers
from app.entry.http.router import api_router
from app.modules import model_registry as _model_registry  # noqa: F401
from app.shared.db import SessionFactory, create_session_factory
from app.shared.settings import validate_startup_settings


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    validate_startup_settings()
    yield


def create_app(
    *,
    session_factory: SessionFactory | None = None,
    database_url: str | None = None,
) -> FastAPI:
    app = FastAPI(title="easyStory API", version="0.1.0", lifespan=app_lifespan)
    app.state.session_factory = session_factory or create_session_factory(database_url)
    register_error_handlers(app)
    register_cors(app)
    app.include_router(api_router)
    return app


app = create_app()
