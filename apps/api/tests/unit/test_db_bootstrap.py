from __future__ import annotations

from app.shared.db import resolve_async_database_url


def test_resolve_async_database_url_upgrades_sqlite_driver() -> None:
    assert (
        resolve_async_database_url("sqlite:///tmp/easystory.db")
        == "sqlite+aiosqlite:///tmp/easystory.db"
    )


def test_resolve_async_database_url_preserves_existing_async_driver() -> None:
    assert (
        resolve_async_database_url("sqlite+aiosqlite:///tmp/easystory.db")
        == "sqlite+aiosqlite:///tmp/easystory.db"
    )
