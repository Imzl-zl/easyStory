from __future__ import annotations

from app.main import create_app
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.test_preparation_api import TEST_JWT_SECRET

LOCAL_WEB_ORIGIN = "http://127.0.0.1:3000"


async def test_auth_register_allows_local_web_cors_preflight(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="auth-api-cors")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        async with started_async_client(app) as client:
            response = await client.options(
                "/api/v1/auth/register",
                headers={
                    "Origin": LOCAL_WEB_ORIGIN,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                },
            )
            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == LOCAL_WEB_ORIGIN
            assert "POST" in response.headers["access-control-allow-methods"]
            assert "content-type" in response.headers["access-control-allow-headers"].lower()
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_auth_register_still_issues_token(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="auth-api-register")
    )

    try:
        app = create_app(
            async_session_factory=async_session_factory,
        )
        async with started_async_client(app) as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={"username": "cors_writer", "password": "password123"},
                headers={"Origin": LOCAL_WEB_ORIGIN},
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload["token_type"] == "bearer"
            assert payload["username"] == "cors_writer"
            assert payload["access_token"]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
