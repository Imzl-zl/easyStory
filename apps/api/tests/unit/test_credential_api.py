from __future__ import annotations

from datetime import datetime, timezone
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.modules import model_registry as _model_registry  # noqa: F401
from app.modules.credential.entry.http.router import get_credential_service
from app.modules.credential.infrastructure import CredentialVerificationResult
from app.modules.credential.service import create_credential_service
from app.modules.project.models import Project
from app.modules.user.service import TokenService
from app.shared.db import Base
from tests.unit.models.helpers import create_user

TEST_JWT_SECRET = "test-jwt-secret"
TEST_MASTER_KEY = "credential-master-key-for-tests"


class FakeVerifier:
    def verify(
        self,
        *,
        provider: str,
        api_key: str,
        base_url: str | None,
    ) -> CredentialVerificationResult:
        return CredentialVerificationResult(
            verified_at=datetime.now(timezone.utc),
            message="Credential verified",
        )


def test_credentials_api_create_list_and_verify(monkeypatch):
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    session_factory, engine = _build_session_factory()
    app = create_app(session_factory=session_factory)
    app.dependency_overrides[get_credential_service] = lambda: create_credential_service(
        verifier=FakeVerifier()
    )
    client = TestClient(app)
    owner_id = _seed_owner(session_factory)
    headers = _auth_headers(owner_id)

    try:
        create_response = client.post(
            "/api/v1/credentials",
            json={
                "owner_type": "user",
                "provider": "openai",
                "display_name": "我的 OpenAI",
                "api_key": "sk-secret-1234",
            },
            headers=headers,
        )
        assert create_response.status_code == 200
        payload = create_response.json()
        assert payload["provider"] == "openai"
        assert payload["masked_key"] == "sk-...1234"

        list_response = client.get("/api/v1/credentials", headers=headers)
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

        verify_response = client.post(
            f"/api/v1/credentials/{payload['id']}/verify",
            headers=headers,
        )
        assert verify_response.status_code == 200
        assert verify_response.json()["status"] == "verified"
    finally:
        client.close()
        Base.metadata.drop_all(engine)


def test_credentials_api_hides_other_users_project(monkeypatch):
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    session_factory, engine = _build_session_factory()
    app = create_app(session_factory=session_factory)
    client = TestClient(app)
    project_id, _owner_id = _seed_project(session_factory)
    outsider_id = _seed_owner(session_factory)

    try:
        response = client.post(
            "/api/v1/credentials",
            json={
                "owner_type": "project",
                "project_id": project_id,
                "provider": "openai",
                "display_name": "项目 Key",
                "api_key": "sk-secret-1234",
            },
            headers=_auth_headers(outsider_id),
        )
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
    finally:
        client.close()
        Base.metadata.drop_all(engine)


def test_credentials_api_returns_configuration_error_when_master_key_missing(monkeypatch):
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.delenv("EASYSTORY_CREDENTIAL_MASTER_KEY", raising=False)
    session_factory, engine = _build_session_factory()
    client = TestClient(create_app(session_factory=session_factory))
    owner_id = _seed_owner(session_factory)

    try:
        response = client.post(
            "/api/v1/credentials",
            json={
                "owner_type": "user",
                "provider": "openai",
                "display_name": "我的 OpenAI",
                "api_key": "sk-secret-1234",
            },
            headers=_auth_headers(owner_id),
        )
        assert response.status_code == 500
        assert response.json()["code"] == "configuration_error"
    finally:
        client.close()
        Base.metadata.drop_all(engine)


def _build_session_factory() -> tuple[sessionmaker[Session], object]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(engine, expire_on_commit=False, class_=Session)
    return session_factory, engine


def _seed_project(session_factory: sessionmaker[Session]) -> tuple[str, uuid.UUID]:
    with session_factory() as session:
        owner = create_user(session)
        project = Project(name="API 测试项目", owner_id=owner.id)
        session.add(project)
        session.commit()
        session.refresh(project)
        return str(project.id), owner.id


def _seed_owner(session_factory: sessionmaker[Session]) -> uuid.UUID:
    with session_factory() as session:
        return create_user(session).id


def _auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    token = TokenService().issue_for_user(user_id)
    return {"Authorization": f"Bearer {token}"}
