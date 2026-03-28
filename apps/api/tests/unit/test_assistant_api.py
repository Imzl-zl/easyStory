from __future__ import annotations

from app.main import create_app
from app.modules.assistant.entry.http.router import get_assistant_service
from tests.unit.api_test_support import TEST_JWT_SECRET, auth_headers
from tests.unit.async_api_support import build_sqlite_session_factories, cleanup_sqlite_session_factories, started_async_client
from tests.unit.models.helpers import create_user
from tests.unit.test_assistant_service import (
    _FakeCredentialService,
    _FakeMcpToolCaller,
    _FakeToolProvider,
    _build_config_root,
)
from app.modules.assistant.service.factory import create_assistant_rule_service
from app.modules.assistant.service.assistant_hook_providers import build_assistant_plugin_registry
from app.modules.assistant.service.assistant_service import AssistantService
from app.modules.config_registry import ConfigLoader
from app.modules.project.service import create_project_service
from app.shared.runtime import SkillTemplateRenderer


async def test_assistant_api_requires_auth_and_returns_content(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-api")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id

        config_root = _build_config_root(tmp_path)
        loader = ConfigLoader(config_root)
        tool_provider = _FakeToolProvider()
        service = AssistantService(
            assistant_rule_service=create_assistant_rule_service(),
            config_loader=loader,
            credential_service_factory=_FakeCredentialService,
            project_service=create_project_service(),
            tool_provider=tool_provider,
            template_renderer=SkillTemplateRenderer(),
        )
        service.plugin_registry = build_assistant_plugin_registry(
            service,
            config_loader=loader,
            mcp_tool_caller=_FakeMcpToolCaller(),
        )
        app = create_app(async_session_factory=async_session_factory)
        app.dependency_overrides[get_assistant_service] = lambda: service

        async with started_async_client(app) as client:
            unauthorized = await client.post(
                "/api/v1/assistant/turn",
                json={
                    "skill_id": "skill.assistant.general_chat",
                    "model": {"provider": "openai", "name": "gpt-4o-mini"},
                    "messages": [{"role": "user", "content": "今天有什么新闻？"}],
                },
            )
            authorized = await client.post(
                "/api/v1/assistant/turn",
                headers=auth_headers(owner_id),
                json={
                    "agent_id": "agent.general_assistant",
                    "hook_ids": ["hook.before_news_lookup"],
                    "messages": [{"role": "user", "content": "今天有什么新闻？"}],
                },
            )

        assert unauthorized.status_code == 401
        assert authorized.status_code == 200
        body = authorized.json()
        assert body["content"].startswith("主回复：")
        assert body["skill_id"] == "skill.assistant.general_chat"
        assert body["hook_results"][0]["action_type"] == "mcp"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_api_stream_turn_returns_sse_events(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EASYSTORY_JWT_SECRET", TEST_JWT_SECRET)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-api-stream")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id

        config_root = _build_config_root(tmp_path)
        loader = ConfigLoader(config_root)
        tool_provider = _FakeToolProvider()
        service = AssistantService(
            assistant_rule_service=create_assistant_rule_service(),
            config_loader=loader,
            credential_service_factory=_FakeCredentialService,
            project_service=create_project_service(),
            tool_provider=tool_provider,
            template_renderer=SkillTemplateRenderer(),
        )
        service.plugin_registry = build_assistant_plugin_registry(
            service,
            config_loader=loader,
            mcp_tool_caller=_FakeMcpToolCaller(),
        )
        app = create_app(async_session_factory=async_session_factory)
        app.dependency_overrides[get_assistant_service] = lambda: service

        async with started_async_client(app) as client:
            async with client.stream(
                "POST",
                "/api/v1/assistant/turn",
                headers=auth_headers(owner_id),
                json={
                    "skill_id": "skill.assistant.general_chat",
                    "stream": True,
                    "messages": [{"role": "user", "content": "给我一个故事方向。"}],
                },
            ) as response:
                assert response.status_code == 200
                body = "".join([chunk async for chunk in response.aiter_text()])

        assert "event: chunk" in body
        assert "event: completed" in body
        assert "主回复：" in body
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)
