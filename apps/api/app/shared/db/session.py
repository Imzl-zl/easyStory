from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

AsyncSessionFactory = async_sessionmaker[AsyncSession]


def _require_async_session_factory(request: Request) -> AsyncSessionFactory:
    async_session_factory = getattr(request.app.state, "async_session_factory", None)
    if async_session_factory is None:
        raise RuntimeError("Async database session factory is not configured")
    return async_session_factory


def get_async_session_factory(request: Request) -> AsyncSessionFactory:
    return _require_async_session_factory(request)


async def get_async_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    async_session_factory = _require_async_session_factory(request)
    async with async_session_factory() as session:
        yield session
