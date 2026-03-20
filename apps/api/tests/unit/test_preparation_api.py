from __future__ import annotations

from contextlib import suppress
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.modules import model_registry as _model_registry  # noqa: F401
from app.modules.project.models import Project
from app.modules.user.service import TokenService
from app.shared.db import Base
from tests.unit.models.helpers import create_user

TEST_JWT_SECRET = "test-jwt-secret"


def test_create_app_bootstraps_database_session_factory(monkeypatch):
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    temp_dir = Path(__file__).resolve().parents[2] / ".pytest-tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    database_path = temp_dir / f"bootstrap-{uuid.uuid4().hex}.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    app = create_app(database_url=database_url)
    owner_id = _seed_owner(app.state.session_factory)
    client = TestClient(app)

    try:
        response = client.post(
            f"/api/v1/projects/{uuid.uuid4()}/setting/complete-check",
            headers=_auth_headers(owner_id),
        )
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
    finally:
        client.close()
        with suppress(PermissionError):
            database_path.unlink(missing_ok=True)


def test_auth_register_and_login_issue_tokens(monkeypatch):
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    client = TestClient(create_app(session_factory=session_factory))

    try:
        register_response = client.post(
            "/api/v1/auth/register",
            json={"username": "writer_user", "password": "password123"},
        )
        assert register_response.status_code == 200
        assert register_response.json()["token_type"] == "bearer"
        assert register_response.json()["username"] == "writer_user"

        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "writer_user", "password": "password123"},
        )
        assert login_response.status_code == 200
        assert login_response.json()["access_token"]
    finally:
        client.close()
        Base.metadata.drop_all(engine)


def test_preparation_endpoints_require_authentication(monkeypatch):
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    project_id, _owner_id = _seed_project(session_factory)
    client = TestClient(create_app(session_factory=session_factory))

    try:
        response = client.post(f"/api/v1/projects/{project_id}/setting/complete-check")
        assert response.status_code == 401
        assert response.json()["code"] == "unauthorized"
    finally:
        client.close()
        Base.metadata.drop_all(engine)


def test_preparation_endpoints_hide_other_users_project(monkeypatch):
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    project_id, _owner_id = _seed_project(session_factory)
    outsider_id = _seed_owner(session_factory)
    client = TestClient(create_app(session_factory=session_factory))

    try:
        response = client.post(
            f"/api/v1/projects/{project_id}/setting/complete-check",
            headers=_auth_headers(outsider_id),
        )
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
    finally:
        client.close()
        Base.metadata.drop_all(engine)


def test_preparation_endpoints_drive_outline_to_opening_plan_flow(monkeypatch):
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    project_id, owner_id = _seed_project(session_factory)
    client = TestClient(create_app(session_factory=session_factory))
    headers = _auth_headers(owner_id)

    try:
        outline_blocked = client.put(
            f"/api/v1/projects/{project_id}/outline",
            json={"title": "大纲", "content_text": "第一卷：入宗与逃亡"},
            headers=headers,
        )
        assert outline_blocked.status_code == 422

        setting_response = client.put(
            f"/api/v1/projects/{project_id}/setting",
            json={
                "project_setting": {
                    "genre": "玄幻",
                    "tone": "冷峻",
                    "core_conflict": "主角逃离宗门追杀",
                    "protagonist": {
                        "name": "林渊",
                        "identity": "弃徒",
                        "goal": "重返内门",
                    },
                    "world_setting": {
                        "era_baseline": "宗门割据时代",
                        "world_rules": "强者为尊",
                    },
                    "scale": {"target_words": 900000},
                }
            },
            headers=headers,
        )
        assert setting_response.status_code == 200
        assert setting_response.json()["genre"] == "玄幻"

        check_response = client.post(
            f"/api/v1/projects/{project_id}/setting/complete-check",
            headers=headers,
        )
        assert check_response.status_code == 200
        assert check_response.json()["status"] == "ready"

        opening_plan_blocked = client.put(
            f"/api/v1/projects/{project_id}/opening-plan",
            json={"title": "开篇设计", "content_text": "前三章要建立钩子"},
            headers=headers,
        )
        assert opening_plan_blocked.status_code == 422

        outline_response = client.put(
            f"/api/v1/projects/{project_id}/outline",
            json={"title": "大纲", "content_text": "第一卷：入宗与逃亡"},
            headers=headers,
        )
        assert outline_response.status_code == 200
        assert outline_response.json()["status"] == "draft"

        outline_approve = client.post(
            f"/api/v1/projects/{project_id}/outline/approve",
            headers=headers,
        )
        assert outline_approve.status_code == 200
        assert outline_approve.json()["status"] == "approved"

        opening_plan_response = client.put(
            f"/api/v1/projects/{project_id}/opening-plan",
            json={"title": "开篇设计", "content_text": "前三章建立主角困境"},
            headers=headers,
        )
        assert opening_plan_response.status_code == 200
        assert opening_plan_response.json()["content_type"] == "opening_plan"
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
