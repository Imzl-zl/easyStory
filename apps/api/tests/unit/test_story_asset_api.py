from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.modules import model_registry as _model_registry  # noqa: F401
from app.modules.content.models import Content, ContentVersion
from app.modules.project.models import Project
from app.modules.user.service import TokenService
from app.shared.db import Base
from tests.unit.models.helpers import create_user, ready_project_setting

TEST_JWT_SECRET = "test-jwt-secret"


def test_story_asset_api_supports_outline_and_opening_plan_readback(monkeypatch):
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, engine = _build_session_factory()
    project_id, owner_id = _seed_project_with_assets(session_factory)
    client = TestClient(create_app(session_factory=session_factory))
    headers = _auth_headers(owner_id)

    try:
        outline_response = client.get(f"/api/v1/projects/{project_id}/outline", headers=headers)
        opening_plan_response = client.get(
            f"/api/v1/projects/{project_id}/opening-plan",
            headers=headers,
        )

        assert outline_response.status_code == 200
        assert outline_response.json()["content_type"] == "outline"
        assert outline_response.json()["title"] == "主线大纲"

        assert opening_plan_response.status_code == 200
        assert opening_plan_response.json()["content_type"] == "opening_plan"
        assert opening_plan_response.json()["title"] == "开篇设计"
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


def _seed_project_with_assets(session_factory: sessionmaker[Session]) -> tuple[str, uuid.UUID]:
    with session_factory() as session:
        owner = create_user(session)
        project = Project(
            name="资产 API 测试项目",
            owner_id=owner.id,
            project_setting=ready_project_setting(),
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        _create_asset(session, project.id, "outline", "主线大纲")
        _create_asset(session, project.id, "opening_plan", "开篇设计")
        return str(project.id), owner.id


def _create_asset(
    session: Session,
    project_id: uuid.UUID,
    content_type: str,
    title: str,
) -> None:
    content = Content(
        project_id=project_id,
        content_type=content_type,
        title=title,
        status="approved",
    )
    session.add(content)
    session.flush()
    session.add(
        ContentVersion(
            content_id=content.id,
            version_number=1,
            content_text=f"{title}内容",
            is_current=True,
        )
    )
    session.commit()


def _auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    token = TokenService().issue_for_user(user_id)
    return {"Authorization": f"Bearer {token}"}
