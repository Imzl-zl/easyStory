from __future__ import annotations

import uuid

from sqlalchemy.orm import Session, sessionmaker

from app.main import create_app
from app.modules.content.entry.http.story_asset_router import get_story_asset_generation_service
from app.modules.content.service import create_story_asset_generation_service
from app.modules.credential.infrastructure import CredentialCrypto
from app.modules.credential.models import ModelCredential
from app.modules.workflow.models import ChapterTask
from tests.unit.api_test_support import auth_headers, build_runtime_app
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.models.helpers import create_project, create_template, create_user
from tests.unit.test_story_asset_generation_service import FakeToolProvider

TEST_JWT_SECRET = "test-jwt-secret"
TEST_MASTER_KEY = "credential-master-key-for-generation-tests"


async def test_preparation_chain_requires_opening_plan_approval_before_workflow_start(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="preparation-workflow-opening-plan-gate")
    )
    project_id, owner_id = _seed_project_with_template_and_credential(session_factory)
    app = create_app(async_session_factory=async_session_factory)
    fake_provider = FakeToolProvider("生成大纲：林渊被逐出宗门。", "生成开篇设计：前三章先立困境。")
    app.dependency_overrides[get_story_asset_generation_service] = (
        lambda: create_story_asset_generation_service(tool_provider=fake_provider)
    )
    headers = auth_headers(owner_id)

    try:
        async with started_async_client(app) as client:
            await _complete_project_setting(client, project_id, headers)
            await _generate_and_approve_outline(client, project_id, headers)

            opening_plan_response = await client.post(
                f"/api/v1/projects/{project_id}/opening-plan/generate",
                headers=headers,
            )
            assert opening_plan_response.status_code == 200
            assert opening_plan_response.json()["status"] == "draft"

            start_response = await client.post(
                f"/api/v1/projects/{project_id}/workflows/start",
                headers=headers,
            )

        assert start_response.status_code == 422
        assert "开篇设计必须先确认后才能启动工作流" in start_response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_preparation_chain_generate_approve_then_start_workflow(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="preparation-workflow-full-chain")
    )
    project_id, owner_id = _seed_project_with_template_and_credential(session_factory)
    app = build_runtime_app(session_factory, async_session_factory)
    fake_provider = FakeToolProvider(
        "生成大纲：林渊入宗后遭遇追杀。",
        "生成开篇设计：前三章先压迫，再给反击承诺。",
    )
    app.dependency_overrides[get_story_asset_generation_service] = (
        lambda: create_story_asset_generation_service(tool_provider=fake_provider)
    )
    headers = auth_headers(owner_id)

    try:
        async with started_async_client(app) as client:
            status_response = await _complete_project_setting(client, project_id, headers)
            assert status_response["outline"]["step_status"] == "not_started"
            assert status_response["opening_plan"]["step_status"] == "not_started"
            assert status_response["can_start_workflow"] is False
            assert status_response["next_step"] == "outline"

            await _generate_and_approve_outline(client, project_id, headers)

            opening_plan_response = await client.post(
                f"/api/v1/projects/{project_id}/opening-plan/generate",
                headers=headers,
            )
            assert opening_plan_response.status_code == 200
            assert opening_plan_response.json()["content_type"] == "opening_plan"
            assert opening_plan_response.json()["status"] == "draft"

            approve_opening_plan_response = await client.post(
                f"/api/v1/projects/{project_id}/opening-plan/approve",
                headers=headers,
            )
            assert approve_opening_plan_response.status_code == 200
            assert approve_opening_plan_response.json()["status"] == "approved"

            start_response = await client.post(
                f"/api/v1/projects/{project_id}/workflows/start",
                headers=headers,
            )

        assert start_response.status_code == 200
        body = start_response.json()
        assert body["status"] == "paused"
        assert body["workflow_id"] == "workflow.xuanhuan_manual"
        assert body["current_node_id"] == "chapter_split"
        assert body["resume_from_node"] == "chapter_gen"

        with session_factory() as session:
            tasks = (
                session.query(ChapterTask)
                .filter(ChapterTask.project_id == uuid.UUID(project_id))
                .order_by(ChapterTask.chapter_number.asc())
                .all()
            )
            assert [item.chapter_number for item in tasks] == [1, 2]
            assert [item.status for item in tasks] == ["pending", "pending"]
    finally:
        app.dependency_overrides.clear()
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def _complete_project_setting(client, project_id: str, headers: dict[str, str]) -> dict:
    setting_response = await client.put(
        f"/api/v1/projects/{project_id}/setting",
        json={
            "project_setting": {
                "genre": "玄幻",
                "tone": "冷峻",
                "core_conflict": "主角在宗门追杀中求生",
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
    status_response = await client.get(
        f"/api/v1/projects/{project_id}/preparation/status",
        headers=headers,
    )
    assert status_response.status_code == 200
    return status_response.json()


async def _generate_and_approve_outline(client, project_id: str, headers: dict[str, str]) -> None:
    outline_response = await client.post(
        f"/api/v1/projects/{project_id}/outline/generate",
        headers=headers,
    )
    assert outline_response.status_code == 200
    assert outline_response.json()["status"] == "draft"
    approve_response = await client.post(
        f"/api/v1/projects/{project_id}/outline/approve",
        headers=headers,
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"


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
