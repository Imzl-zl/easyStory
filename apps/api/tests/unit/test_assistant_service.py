from __future__ import annotations

from pathlib import Path
import uuid

import pytest

from app.modules.assistant.service.assistant_config_file_store import AssistantConfigFileStore
from app.modules.assistant.service.assistant_hook_providers import build_assistant_plugin_registry
from app.modules.assistant.service.assistant_service import AssistantService
from app.modules.assistant.service.assistant_rule_dto import AssistantRuleProfileUpdateDTO
from app.modules.assistant.service.preferences_dto import AssistantPreferencesUpdateDTO
from app.modules.assistant.service.preferences_service import AssistantPreferencesService
from app.modules.assistant.service.dto import AssistantMessageDTO, AssistantTurnRequestDTO
from app.modules.assistant.service.factory import create_assistant_rule_service
from app.modules.config_registry import ConfigLoader
from app.modules.credential.models import ModelCredential
from app.modules.project.service import create_project_service
from app.shared.runtime import McpToolCallResult, SkillTemplateRenderer, ToolProvider
from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm_tool_provider import LLMStreamEvent
from tests.unit.async_api_support import build_sqlite_session_factories, cleanup_sqlite_session_factories
from tests.unit.models.helpers import create_project, create_user


class _FakeCrypto:
    def decrypt(self, value: str) -> str:
        return value


class _FakeCredentialService:
    def __init__(self) -> None:
        self.crypto = _FakeCrypto()

    async def resolve_active_credential(self, db, *, provider: str, user_id, project_id=None):
        del db, user_id, project_id
        return ModelCredential(
            owner_type="user",
            owner_id=uuid.uuid4(),
            provider=provider,
            display_name=f"{provider}-test",
            encrypted_key=f"{provider}-key",
            api_dialect="openai_responses",
            default_model="gpt-4o-mini",
            is_active=True,
        )


class _FakeToolProvider(ToolProvider):
    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.requests: list[dict[str, object | None]] = []

    async def execute(self, tool_name: str, params: dict) -> dict:
        assert tool_name == "llm.generate"
        prompt = params["prompt"]
        self.prompts.append(prompt)
        self.requests.append(
            {
                "prompt": prompt,
                "response_format": params["response_format"],
                "system_prompt": params.get("system_prompt"),
                "model": params.get("model"),
            }
        )
        if "请输出结构化摘要" in prompt:
            return {
                "content": '{"summary":"今天的新闻聚焦科技与国际局势。","sentiment":"neutral"}',
                "input_tokens": 4,
                "output_tokens": 8,
                "total_tokens": 12,
            }
        if "请根据以下内容输出一句摘要" in prompt:
            return {"content": "Hook 摘要完成。", "input_tokens": 3, "output_tokens": 5, "total_tokens": 8}
        return {
            "content": "主回复：今天的重点新闻主要集中在科技和国际动态。",
            "model_name": "gpt-4o-mini",
            "input_tokens": 11,
            "output_tokens": 19,
            "total_tokens": 30,
        }

    async def execute_stream(self, tool_name: str, params: dict, *, should_stop=None):
        del should_stop
        result = await self.execute(tool_name, params)
        content = result["content"]
        midpoint = max(1, len(content) // 2)
        yield LLMStreamEvent(delta=content[:midpoint])
        yield LLMStreamEvent(delta=content[midpoint:])
        yield LLMStreamEvent(response=result)

    def list_tools(self) -> list[str]:
        return ["llm.generate"]


class _FakeMcpToolCaller:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    async def call_tool(self, *, server, tool_name: str, arguments: dict) -> McpToolCallResult:
        self.calls.append((server.id, tool_name, arguments))
        return McpToolCallResult(
            content=[{"type": "text", "text": "来自 MCP 的查询结果"}],
            structured_content={"headline": "今日热点"},
            is_error=False,
        )


class _ErrorMcpToolCaller(_FakeMcpToolCaller):
    async def call_tool(self, *, server, tool_name: str, arguments: dict) -> McpToolCallResult:
        self.calls.append((server.id, tool_name, arguments))
        return McpToolCallResult(
            content=[{"type": "text", "text": "上游返回错误"}],
            structured_content={"message": "上游返回错误"},
            is_error=True,
        )


async def test_assistant_service_runs_skill_and_mcp_hook(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    mcp_tool_caller = _FakeMcpToolCaller()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(
        service,
        config_loader=loader,
        mcp_tool_caller=mcp_tool_caller,
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-service")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            payload = AssistantTurnRequestDTO(
                agent_id="agent.general_assistant",
                hook_ids=["hook.before_news_lookup"],
                messages=[AssistantMessageDTO(role="user", content="今天有什么新闻？")],
            )
            response = await service.turn(session, payload, owner_id=owner_id)

        assert response.content.startswith("主回复：")
        assert response.skill_id == "skill.assistant.general_chat"
        assert response.mcp_servers == ["mcp.news.lookup"]
        assert response.hook_results[0].action_type == "mcp"
        assert mcp_tool_caller.calls == [
            ("mcp.news.lookup", "search_news", {"query": "今天有什么新闻？"})
        ]
        assert "今天有什么新闻？" in tool_provider.prompts[0]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_stream_turn_yields_chunks_and_completed_event(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(service, config_loader=loader)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-stream-service")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            payload = AssistantTurnRequestDTO(
                skill_id="skill.assistant.general_chat",
                stream=True,
                messages=[AssistantMessageDTO(role="user", content="给我一个故事方向。")],
            )
            events = [
                event async for event in service.stream_turn(session, payload, owner_id=owner_id)
            ]

        assert [event.event for event in events] == ["chunk", "chunk", "completed"]
        assert "".join(event.data["delta"] for event in events[:-1]) == (
            "主回复：今天的重点新闻主要集中在科技和国际动态。"
        )
        assert events[-1].data["content"].startswith("主回复：")
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_runs_agent_hook_after_response(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(service, config_loader=loader)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-agent-hook")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            payload = AssistantTurnRequestDTO(
                skill_id="skill.assistant.general_chat",
                hook_ids=["hook.after_summary_agent"],
                model={"provider": "openai", "name": "gpt-4o-mini"},
                messages=[AssistantMessageDTO(role="user", content="帮我看看今天的新闻。")],
            )
            response = await service.turn(session, payload, owner_id=owner_id)

        assert response.content.startswith("主回复：")
        assert response.hook_results[0].action_type == "agent"
        assert response.hook_results[0].result == "Hook 摘要完成。"
        assert any("请根据以下内容输出一句摘要" in prompt for prompt in tool_provider.prompts)
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_applies_preferences_and_rules_to_agent_hook(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        assistant_preferences_service=AssistantPreferencesService(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(service, config_loader=loader)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-agent-hook-preferences")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
        async with async_session_factory() as session:
            await service.assistant_preferences_service.update_preferences(
                session,
                owner.id,
                AssistantPreferencesUpdateDTO(
                    default_provider="anthropic",
                    default_model_name="claude-sonnet-4",
                ),
            )
            await service.assistant_rule_service.update_user_rules(
                session,
                payload=AssistantRuleProfileUpdateDTO(enabled=True, content="先给结论。"),
                owner_id=owner.id,
            )
            await service.assistant_rule_service.update_project_rules(
                session,
                project.id,
                payload=AssistantRuleProfileUpdateDTO(
                    enabled=True,
                    content="这个项目统一写得更温柔一点。",
                ),
                owner_id=owner.id,
            )
            payload = AssistantTurnRequestDTO(
                skill_id="skill.assistant.general_chat",
                project_id=project.id,
                hook_ids=["hook.after_summary_agent"],
                messages=[AssistantMessageDTO(role="user", content="帮我看看今天的新闻。")],
            )
            await service.turn(session, payload, owner_id=owner.id)

        hook_request = tool_provider.requests[-1]
        model = hook_request["model"]
        system_prompt = hook_request["system_prompt"] or ""
        assert isinstance(model, dict)
        assert model["provider"] == "anthropic"
        assert model["name"] == "claude-sonnet-4"
        assert "【用户长期规则】" in system_prompt
        assert "先给结论。" in system_prompt
        assert "【当前项目规则】" in system_prompt
        assert "这个项目统一写得更温柔一点。" in system_prompt
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_injects_user_and_project_rules(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(service, config_loader=loader)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-rules")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
        async with async_session_factory() as session:
            await service.assistant_rule_service.update_user_rules(
                session,
                payload=AssistantRuleProfileUpdateDTO(enabled=True, content="回答时先给结论。"),
                owner_id=owner.id,
            )
            await service.assistant_rule_service.update_project_rules(
                session,
                project.id,
                payload=AssistantRuleProfileUpdateDTO(
                    enabled=True,
                    content="这个项目固定写成轻松治愈风。",
                ),
                owner_id=owner.id,
            )
            payload = AssistantTurnRequestDTO(
                agent_id="agent.general_assistant",
                project_id=project.id,
                messages=[AssistantMessageDTO(role="user", content="给我一个开头方向。")],
            )
            await service.turn(session, payload, owner_id=owner.id)

        system_prompt = tool_provider.requests[0]["system_prompt"] or ""
        assert "【用户长期规则】" in system_prompt
        assert "回答时先给结论。" in system_prompt
        assert "【当前项目规则】" in system_prompt
        assert "这个项目固定写成轻松治愈风。" in system_prompt
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_applies_user_model_preferences(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        assistant_preferences_service=AssistantPreferencesService(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(service, config_loader=loader)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-preferences")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
        async with async_session_factory() as session:
            await service.assistant_preferences_service.update_preferences(
                session,
                owner.id,
                AssistantPreferencesUpdateDTO(
                    default_provider="anthropic",
                    default_model_name="claude-sonnet-4",
                ),
            )
            payload = AssistantTurnRequestDTO(
                skill_id="skill.assistant.general_chat",
                messages=[AssistantMessageDTO(role="user", content="给我一个故事方向。")],
            )
            await service.turn(session, payload, owner_id=owner.id)

        model = tool_provider.requests[0]["model"]
        assert isinstance(model, dict)
        assert model["provider"] == "anthropic"
        assert model["name"] == "claude-sonnet-4"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_runs_structured_agent_hook_after_response(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    _write_yaml(
        config_root / "skills" / "assistant" / "hook-structured-summary.yaml",
        """
skill:
  id: "skill.assistant.hook_structured_summary"
  name: "结构化 Hook 摘要"
  category: "assistant"
  prompt: |
    请输出结构化摘要：
    {{ content }}
  variables:
    content:
      type: "string"
      required: true
  model:
    provider: "openai"
    name: "gpt-4o-mini"
""",
    )
    _write_yaml(
        config_root / "agents" / "writers" / "hook-structured-summary.yaml",
        """
agent:
  id: "agent.hook_structured_summary"
  name: "结构化 Hook 摘要助手"
  type: "checker"
  system_prompt: "你负责把回复整理成结构化摘要。"
  skills: ["skill.assistant.hook_structured_summary"]
  output_schema:
    type: "object"
    properties:
      summary:
        type: "string"
      sentiment:
        type: "string"
  model:
    provider: "openai"
    name: "gpt-4o-mini"
""",
    )
    _write_yaml(
        config_root / "hooks" / "after-structured-summary-agent.yaml",
        """
hook:
  id: "hook.after_structured_summary_agent"
  name: "生成结构化摘要"
  trigger:
    event: "after_assistant_response"
  action:
    type: "agent"
    config:
      agent_id: "agent.hook_structured_summary"
      input_mapping:
        content: "response.content"
""",
    )
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(service, config_loader=loader)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-structured-hook")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            payload = AssistantTurnRequestDTO(
                skill_id="skill.assistant.general_chat",
                hook_ids=["hook.after_structured_summary_agent"],
                model={"provider": "openai", "name": "gpt-4o-mini"},
                messages=[AssistantMessageDTO(role="user", content="帮我整理一下今天的新闻。")],
            )
            response = await service.turn(session, payload, owner_id=owner_id)

        assert response.content.startswith("主回复：")
        assert response.hook_results[0].result == {
            "summary": "今天的新闻聚焦科技与国际局势。",
            "sentiment": "neutral",
        }
        structured_call = next(
            item for item in tool_provider.requests if "请输出结构化摘要" in item["prompt"]
        )
        assert structured_call["response_format"] == "json_object"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_rejects_mcp_hook_when_server_disabled(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    _write_yaml(
        config_root / "mcp_servers" / "news.yaml",
        """
mcp_server:
  id: "mcp.news.lookup"
  name: "新闻检索 MCP"
  transport: "streamable_http"
  url: "https://example.com/mcp"
  enabled: false
""",
    )
    loader = ConfigLoader(config_root)
    mcp_tool_caller = _FakeMcpToolCaller()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=_FakeToolProvider(),
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(
        service,
        config_loader=loader,
        mcp_tool_caller=mcp_tool_caller,
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-mcp-disabled")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            payload = AssistantTurnRequestDTO(
                agent_id="agent.general_assistant",
                hook_ids=["hook.before_news_lookup"],
                messages=[AssistantMessageDTO(role="user", content="今天有什么新闻？")],
            )
            with pytest.raises(ConfigurationError, match="disabled"):
                await service.turn(session, payload, owner_id=owner_id)
        assert mcp_tool_caller.calls == []
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_service_surfaces_mcp_is_error(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    mcp_tool_caller = _ErrorMcpToolCaller()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=_FakeToolProvider(),
        template_renderer=SkillTemplateRenderer(),
    )
    service.plugin_registry = build_assistant_plugin_registry(
        service,
        config_loader=loader,
        mcp_tool_caller=mcp_tool_caller,
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-mcp-error")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
        async with async_session_factory() as session:
            payload = AssistantTurnRequestDTO(
                agent_id="agent.general_assistant",
                hook_ids=["hook.before_news_lookup"],
                messages=[AssistantMessageDTO(role="user", content="今天有什么新闻？")],
            )
            with pytest.raises(RuntimeError, match="is_error=true"):
                await service.turn(session, payload, owner_id=owner_id)
        assert mcp_tool_caller.calls == [
            ("mcp.news.lookup", "search_news", {"query": "今天有什么新闻？"})
        ]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def _build_config_root(tmp_path: Path) -> Path:
    root = tmp_path / "config"
    _write_yaml(
        root / "skills" / "assistant" / "general-chat.yaml",
        """
skill:
  id: "skill.assistant.general_chat"
  name: "通用对话助手"
  category: "assistant"
  prompt: |
    你是一个通用助手。
    {% if conversation_history %}
    历史对话：
    {{ conversation_history }}
    {% endif %}
    用户问题：{{ user_input }}
  variables:
    conversation_history:
      type: "string"
      required: false
      default: ""
    user_input:
      type: "string"
      required: true
  model:
    provider: "openai"
    name: "gpt-4o-mini"
""",
    )
    _write_yaml(
        root / "skills" / "assistant" / "hook-summary.yaml",
        """
skill:
  id: "skill.assistant.hook_summary"
  name: "Hook 摘要"
  category: "assistant"
  prompt: |
    请根据以下内容输出一句摘要：
    {{ content }}
  variables:
    content:
      type: "string"
      required: true
  model:
    provider: "openai"
    name: "gpt-4o-mini"
""",
    )
    _write_yaml(
        root / "agents" / "writers" / "general-assistant.yaml",
        """
agent:
  id: "agent.general_assistant"
  name: "通用助手"
  type: "writer"
  system_prompt: "你是通用助手。"
  skills: ["skill.assistant.general_chat"]
  mcp_servers: ["mcp.news.lookup"]
  model:
    provider: "openai"
    name: "gpt-4o-mini"
""",
    )
    _write_yaml(
        root / "agents" / "writers" / "hook-summary.yaml",
        """
agent:
  id: "agent.hook_summary"
  name: "Hook 摘要助手"
  type: "checker"
  system_prompt: "你负责给正文做一句摘要。"
  skills: ["skill.assistant.hook_summary"]
  model:
    provider: "openai"
    name: "gpt-4o-mini"
""",
    )
    _write_yaml(
        root / "hooks" / "before-news-lookup.yaml",
        """
hook:
  id: "hook.before_news_lookup"
  name: "新闻检索"
  trigger:
    event: "before_assistant_response"
  action:
    type: "mcp"
    config:
      server_id: "mcp.news.lookup"
      tool_name: "search_news"
      input_mapping:
        query: "request.user_input"
""",
    )
    _write_yaml(
        root / "hooks" / "after-summary-agent.yaml",
        """
hook:
  id: "hook.after_summary_agent"
  name: "生成摘要"
  trigger:
    event: "after_assistant_response"
  action:
    type: "agent"
    config:
      agent_id: "agent.hook_summary"
      input_mapping:
        content: "response.content"
""",
    )
    _write_yaml(
        root / "mcp_servers" / "news.yaml",
        """
mcp_server:
  id: "mcp.news.lookup"
  name: "新闻检索 MCP"
  transport: "streamable_http"
  url: "https://example.com/mcp"
""",
    )
    return root


def _write_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
