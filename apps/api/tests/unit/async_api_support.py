from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
import uuid

import httpx
from fastapi import FastAPI
from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.shared.db import Base


def build_sqlite_session_factories(
    tmp_path: Path,
    *,
    name: str,
) -> tuple[
    sessionmaker[Session],
    async_sessionmaker[AsyncSession],
    Engine,
    AsyncEngine,
    Path,
]:
    database_path = tmp_path / f"{name}-{uuid.uuid4().hex}.db"
    sync_url = f"sqlite:///{database_path.as_posix()}"
    async_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    sync_engine = create_engine(sync_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()
    async_engine = create_async_engine(async_url)
    sync_factory = sessionmaker(sync_engine, expire_on_commit=False, class_=Session)
    async_factory = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)
    return sync_factory, async_factory, sync_engine, async_engine, database_path


async def cleanup_sqlite_session_factories(
    sync_engine: Engine,
    async_engine: AsyncEngine,
    database_path: Path,
) -> None:
    sync_engine.dispose()
    await async_engine.dispose()
    with suppress(FileNotFoundError, PermissionError):
        database_path.unlink()


@asynccontextmanager
async def started_async_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            yield client
