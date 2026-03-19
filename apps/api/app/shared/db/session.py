from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session, sessionmaker

SessionFactory = sessionmaker[Session]


def get_session_factory(request: Request) -> SessionFactory:
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        raise RuntimeError("Database session factory is not configured")
    return session_factory


def get_db_session(request: Request) -> Iterator[Session]:
    session_factory = get_session_factory(request)
    with session_factory() as session:
        yield session
