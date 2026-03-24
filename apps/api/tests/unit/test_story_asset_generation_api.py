from __future__ import annotations

import uuid

from sqlalchemy.orm import Session, sessionmaker

from app.main import create_app
from app.modules.content.entry.http.story_asset_router import get_story_asset_generation_service
from app.modules.content.service import create_story_asset_generation_service
from app.modules.credential.infrastructure import CredentialCrypto
from app.modules.credential.models import ModelCredential
from app.modules.user.service import TokenService
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.test_story_asset_generation_service import FakeToolProvider
from tests.unit.models.helpers import create_project, create_template, create_user, ready_project_setting

TEST_JWT_SECRET = "test-jwt-secret"
TEST_MASTER_KEY = "credential-master-key-for-generation-tests"


async def test_story_asset_generate_api_generates_outline_then_opening_plan(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="story-asset-generate-api")
    )
    project_id, owner_id = _seed_project_with_template_and_credential(session_factory)
    app = create_app(async_session_factory=async_session_factory)
    fake_provider = FakeToolProvider(
        "生成大纲：林渊入宗后被迫逃亡。",
        "生成开篇设计：前三章先压迫，再给反击承诺。",
    )
    app.dependency_overrides[get_story_asset_generation_service] = (
        lambda: create_story_asset_generation_service(tool_provider=fake_provider)
    )

    try:
        async with started_async_client(app) as client:
            outline_response = await client.post(
                f"/api/v1/projects/{project_id}/outline/generate",
                headers=_auth_headers(owner_id),
            )
            assert outline_response.status_code == 200
            assert outline_response.json()["content_type"] == "outline"
            assert outline_response.json()["content_text"] == "生成大纲：林渊入宗后被迫逃亡。"
            assert outline_response.json()["impact"]["has_impact"] is False

            approve_response = await client.post(
                f"/api/v1/projects/{project_id}/outline/approve",
                headers=_auth_headers(owner_id),
            )
            assert approve_response.status_code == 200
            assert approve_response.json()["status"] == "approved"
            assert approve_response.json()["impact"]["has_impact"] is False

            opening_plan_response = await client.post(
                f"/api/v1/projects/{project_id}/opening-plan/generate",
                headers=_auth_headers(owner_id),
            )
            assert opening_plan_response.status_code == 200
            assert opening_plan_response.json()["content_type"] == "opening_plan"
            assert opening_plan_response.json()["impact"]["has_impact"] is False
            assert (
                opening_plan_response.json()["content_text"]
                == "生成开篇设计：前三章先压迫，再给反击承诺。"
            )
    finally:
        app.dependency_overrides.clear()
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_story_asset_generate_api_accepts_explicit_workflow_id(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="story-asset-generate-api-explicit")
    )
    project_id, owner_id = _seed_project_with_credential_only(session_factory)
    app = create_app(async_session_factory=async_session_factory)
    fake_provider = FakeToolProvider("显式 workflow 生成大纲。")
    app.dependency_overrides[get_story_asset_generation_service] = (
        lambda: create_story_asset_generation_service(tool_provider=fake_provider)
    )

    try:
        async with started_async_client(app) as client:
            response = await client.post(
                f"/api/v1/projects/{project_id}/outline/generate",
                json={"workflow_id": "workflow.xuanhuan_manual"},
                headers=_auth_headers(owner_id),
            )
            assert response.status_code == 200
            assert response.json()["content_text"] == "显式 workflow 生成大纲。"
            assert response.json()["impact"]["has_impact"] is False
    finally:
        app.dependency_overrides.clear()
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def _seed_project_with_template_and_credential(
    session_factory: sessionmaker[Session],
) -> tuple[str, uuid.UUID]:
    with session_factory() as session:
        owner = create_user(session)
        template = create_template(session)
        project = create_project(
            session,
            owner=owner,
            template_id=template.id,
            project_setting=ready_project_setting(),
        )
        _create_anthropic_credential(session, owner.id)
        return str(project.id), owner.id


def _seed_project_with_credential_only(
    session_factory: sessionmaker[Session],
) -> tuple[str, uuid.UUID]:
    with session_factory() as session:
        owner = create_user(session)
        project = create_project(
            session,
            owner=owner,
            project_setting=ready_project_setting(),
        )
        _create_anthropic_credential(session, owner.id)
        return str(project.id), owner.id


def _create_anthropic_credential(session: Session, owner_id: uuid.UUID) -> None:
    crypto = CredentialCrypto()
    session.add(
        ModelCredential(
            owner_type="user",
            owner_id=owner_id,
            provider="anthropic",
            display_name="Anthropic",
            encrypted_key=crypto.encrypt("sk-anthropic-test"),
            is_active=True,
        )
    )
    session.commit()


def _auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    token = TokenService().issue_for_user(user_id)
    return {"Authorization": f"Bearer {token}"}
