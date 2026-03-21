from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from tests.unit.test_preparation_api import TEST_JWT_SECRET, _build_session_factory

LOCAL_WEB_ORIGIN = "http://127.0.0.1:3000"


def test_auth_register_allows_local_web_cors_preflight(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    client = TestClient(create_app(session_factory=session_factory))

    try:
        response = client.options(
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
        client.close()
        engine.dispose()


def test_auth_register_still_issues_token(monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    client = TestClient(create_app(session_factory=session_factory))

    try:
        response = client.post(
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
        client.close()
        engine.dispose()
