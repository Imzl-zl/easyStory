from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.shared.settings import get_settings

from .base import Base

DEFAULT_DB_DIR = ".runtime"
DEFAULT_DB_NAME = "easystory.db"


def create_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def create_database_engine(database_url: str | None = None) -> Engine:
    resolved_url = resolve_database_url(database_url)
    return create_engine(resolved_url, **_engine_kwargs(resolved_url))


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


def _engine_kwargs(database_url: str) -> dict:
    if not database_url.startswith("sqlite"):
        return {}
    kwargs: dict[str, object] = {"connect_args": {"check_same_thread": False}}
    if _is_memory_sqlite(database_url):
        kwargs["poolclass"] = StaticPool
    return kwargs


def _is_memory_sqlite(database_url: str) -> bool:
    return database_url in {"sqlite://", "sqlite:///:memory:"} or ":memory:" in database_url
