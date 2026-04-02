from __future__ import annotations

from app.main import create_app
from app.modules.project.entry.http.router import get_project_incubator_service
from app.modules.project.service import create_project_incubator_service
from app.modules.project.service.dto import (
    PROJECT_INCUBATOR_CONVERSATION_TEXT_MAX_LENGTH,
)
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers as _auth_headers
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
    started_async_client,
)
from tests.unit.models.helpers import create_user
from tests.unit.test_project_incubator_service import (
    TEST_MASTER_KEY,
    FakeConversationToolProvider,
    create_model_credential,
)


async def test_project_incubator_api_builds_project_setting_draft(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-incubator-api")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id

        app = create_app(async_session_factory=async_session_factory)
        async with started_async_client(app) as client:
            templates_response = await client.get(
                "/api/v1/templates",
                headers=_auth_headers(owner_id),
            )
            template_id = templates_response.json()[0]["id"]

            response = await client.post(
                "/api/v1/projects/incubator/draft-setting",
                headers=_auth_headers(owner_id),
                json={
                    "template_id": template_id,
                    "answers": [
                        {"variable": "protagonist", "value": "宗门弃徒"},
                        {"variable": "world_setting", "value": "灵气衰退后的修真界"},
                        {
                            "variable": "core_conflict",
                            "value": "主角被追杀后试图重返宗门",
                        },
                    ],
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["template"]["name"] == "玄幻小说模板"
        assert body["project_setting"]["genre"] == "玄幻"
        assert body["project_setting"]["protagonist"]["identity"] == "宗门弃徒"
        assert body["project_setting"]["world_setting"]["era_baseline"] == "灵气衰退后的修真界"
        assert body["project_setting"]["core_conflict"] == "主角被追杀后试图重返宗门"
        assert body["setting_completeness"]["status"] == "warning"
        assert [item["field"] for item in body["setting_completeness"]["issues"]] == [
            "protagonist.goal",
            "tone",
            "scale",
        ]
        assert [item["field_path"] for item in body["applied_answers"]] == [
            "protagonist.identity",
            "world_setting.era_baseline",
            "core_conflict",
        ]
        assert body["unmapped_answers"] == []
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_incubator_api_requires_auth_and_surfaces_business_errors(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-incubator-api-rules")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id

        app = create_app(async_session_factory=async_session_factory)
        async with started_async_client(app) as client:
            unauthorized = await client.post(
                "/api/v1/projects/incubator/draft-setting",
                json={"template_id": "00000000-0000-0000-0000-000000000000", "answers": []},
            )
            assert unauthorized.status_code == 401

            templates_response = await client.get(
                "/api/v1/templates",
                headers=_auth_headers(owner_id),
            )
            template_id = templates_response.json()[0]["id"]

            invalid = await client.post(
                "/api/v1/projects/incubator/draft-setting",
                headers=_auth_headers(owner_id),
                json={
                    "template_id": template_id,
                    "answers": [{"variable": "not_declared", "value": "x"}],
                },
            )

        assert invalid.status_code == 422
        assert invalid.json()["code"] == "business_rule_error"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_incubator_api_creates_project_from_template_answers(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-incubator-api-create")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id

        app = create_app(async_session_factory=async_session_factory)
        async with started_async_client(app) as client:
            templates_response = await client.get(
                "/api/v1/templates",
                headers=_auth_headers(owner_id),
            )
            template_id = templates_response.json()[0]["id"]

            response = await client.post(
                "/api/v1/projects/incubator/create-project",
                headers=_auth_headers(owner_id),
                json={
                    "name": "模板一键创建项目",
                    "template_id": template_id,
                    "allow_system_credential_pool": True,
                    "answers": [
                        {"variable": "protagonist", "value": "宗门弃徒"},
                        {"variable": "world_setting", "value": "灵气衰退后的修真界"},
                        {
                            "variable": "core_conflict",
                            "value": "主角被追杀后试图重返宗门",
                        },
                    ],
                },
            )

            assert response.status_code == 200
            body = response.json()
            project_id = body["project"]["id"]
            assert body["project"]["name"] == "模板一键创建项目"
            assert body["project"]["template_id"] == template_id
            assert body["project"]["allow_system_credential_pool"] is True
            assert body["project"]["project_setting"]["genre"] == "玄幻"
            assert body["project"]["project_setting"]["core_conflict"] == "主角被追杀后试图重返宗门"
            assert body["setting_completeness"]["status"] == "warning"
            assert [item["field"] for item in body["setting_completeness"]["issues"]] == [
                "protagonist.goal",
                "tone",
                "scale",
            ]
            assert [item["field_path"] for item in body["applied_answers"]] == [
                "protagonist.identity",
                "world_setting.era_baseline",
                "core_conflict",
            ]
            assert body["unmapped_answers"] == []

            outline_response = await client.get(
                f"/api/v1/projects/{project_id}/outline",
                headers=_auth_headers(owner_id),
            )
            opening_plan_response = await client.get(
                f"/api/v1/projects/{project_id}/opening-plan",
                headers=_auth_headers(owner_id),
            )

        assert outline_response.status_code == 200
        assert opening_plan_response.status_code == 200
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_incubator_api_rejects_blank_answer_value(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-incubator-api-blank")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id

        app = create_app(async_session_factory=async_session_factory)
        async with started_async_client(app) as client:
            templates_response = await client.get(
                "/api/v1/templates",
                headers=_auth_headers(owner_id),
            )
            template_id = templates_response.json()[0]["id"]

            response = await client.post(
                "/api/v1/projects/incubator/draft-setting",
                headers=_auth_headers(owner_id),
                json={
                    "template_id": template_id,
                    "answers": [{"variable": "protagonist", "value": "   "}],
                },
            )

        assert response.status_code == 422
        assert response.json()["code"] == "business_rule_error"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_incubator_api_builds_conversation_project_setting_draft(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(
            tmp_path,
            name="project-incubator-conversation-api",
        )
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
            create_model_credential(
                session,
                owner_id,
                provider="anthropic",
                api_dialect="anthropic_messages",
                default_model="claude-sonnet-4-20250514",
            )

        fake_provider = FakeConversationToolProvider(
            {
                "genre": "玄幻修仙",
                "core_conflict": "主角必须在宗门压制中夺回成长机会",
                "protagonist": {
                    "identity": "没落家族少年",
                    "goal": "恢复天赋，为家族复仇",
                },
                "world_setting": {
                    "era_baseline": "宗门林立、强者为尊",
                },
            }
        )
        app = create_app(async_session_factory=async_session_factory)
        app.dependency_overrides[get_project_incubator_service] = lambda: (
            create_project_incubator_service(
                tool_provider=fake_provider
            )
        )
        async with started_async_client(app) as client:
            response = await client.post(
                "/api/v1/projects/incubator/conversation/draft-setting",
                headers=_auth_headers(owner_id),
                json={
                    "conversation_text": (
                        "我想写一本玄幻修仙小说，主角是没落家族少年，"
                        "要在宗门压制中夺回成长机会。"
                    ),
                    "provider": "anthropic",
                    "model_name": "claude-3-7-sonnet-20250219",
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["project_setting"]["genre"] == "玄幻修仙"
        assert body["project_setting"]["protagonist"]["identity"] == "没落家族少年"
        assert body["setting_completeness"]["status"] == "warning"
        assert [item["field"] for item in body["setting_completeness"]["issues"]] == [
            "tone",
            "scale",
        ]
        assert body["follow_up_questions"] == [
            "你希望整体基调或文风更偏什么感觉？",
            "这本书大概准备写多少字，或者规划多少章？",
        ]
        assert fake_provider.params[0]["model"]["provider"] == "anthropic"
        assert fake_provider.params[0]["model"]["name"] == "claude-3-7-sonnet-20250219"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_incubator_conversation_api_requires_auth_and_surfaces_business_errors(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    too_long_conversation = "设" * (
        PROJECT_INCUBATOR_CONVERSATION_TEXT_MAX_LENGTH + 1
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(
            tmp_path,
            name="project-incubator-conversation-api-rules",
        )
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id

        app = create_app(async_session_factory=async_session_factory)
        async with started_async_client(app) as client:
            unauthorized = await client.post(
                "/api/v1/projects/incubator/conversation/draft-setting",
                json={
                    "conversation_text": "我想写一本修仙小说。",
                    "provider": "openai",
                },
            )
            assert unauthorized.status_code == 401

            invalid = await client.post(
                "/api/v1/projects/incubator/conversation/draft-setting",
                headers=_auth_headers(owner_id),
                json={
                    "conversation_text": "   ",
                    "provider": "openai",
                },
            )
            too_long = await client.post(
                "/api/v1/projects/incubator/conversation/draft-setting",
                headers=_auth_headers(owner_id),
                json={
                    "conversation_text": too_long_conversation,
                    "provider": "openai",
                },
            )

        assert invalid.status_code == 422
        assert invalid.json()["code"] == "business_rule_error"
        assert too_long.status_code == 422
        assert too_long.json()["detail"][0]["type"] == "string_too_long"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
