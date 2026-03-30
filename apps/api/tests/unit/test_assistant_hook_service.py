from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.assistant.service import (
    AssistantAgentCreateDTO,
    AssistantAgentService,
    AssistantMcpCreateDTO,
    AssistantMcpService,
    AssistantHookCreateDTO,
    AssistantHookService,
    AssistantHookUpdateDTO,
    AssistantSkillCreateDTO,
    AssistantSkillService,
)
from app.modules.assistant.service.assistant_agent_file_store import AssistantAgentFileStore
from app.modules.assistant.service.assistant_hook_file_store import AssistantHookFileStore
from app.modules.assistant.service.assistant_mcp_file_store import AssistantMcpFileStore
from app.modules.assistant.service.assistant_user_hook_support import parse_hook_document
from app.modules.assistant.service.assistant_skill_file_store import AssistantSkillFileStore
from app.modules.config_registry import ConfigLoader
from app.modules.project.service import create_project_service
from app.shared.runtime.errors import ConfigurationError
from tests.unit.async_api_support import build_sqlite_session_factories, cleanup_sqlite_session_factories
from tests.unit.models.helpers import create_user
from tests.unit.test_assistant_service import _build_config_root


async def test_assistant_hook_service_creates_updates_and_deletes_user_hook(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    skill_service = AssistantSkillService(
        config_loader=loader,
        project_service=create_project_service(),
        skill_store=AssistantSkillFileStore(tmp_path / "assistant-config"),
    )
    agent_service = AssistantAgentService(
        assistant_skill_service=skill_service,
        config_loader=loader,
        agent_store=AssistantAgentFileStore(tmp_path / "assistant-config"),
    )
    mcp_service = AssistantMcpService(
        config_loader=loader,
        project_service=create_project_service(),
        mcp_store=AssistantMcpFileStore(tmp_path / "assistant-config"),
    )
    hook_service = AssistantHookService(
        assistant_agent_service=agent_service,
        assistant_mcp_service=mcp_service,
        config_loader=loader,
        hook_store=AssistantHookFileStore(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-hook-service")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
        async with async_session_factory() as session:
            created_skill = await skill_service.create_user_skill(
                session,
                AssistantSkillCreateDTO(name="Hook 摘要 Skill", content="请根据以下内容输出一句摘要：\n{{ user_input }}"),
                owner_id=owner.id,
            )
            created_agent = await agent_service.create_user_agent(
                session,
                AssistantAgentCreateDTO(
                    name="Hook 摘要 Agent",
                    skill_id=created_skill.id,
                    system_prompt="你负责把内容整理成一句摘要。",
                ),
                owner_id=owner.id,
            )
            created_hook = await hook_service.create_user_hook(
                session,
                AssistantHookCreateDTO(
                    name="回复后自动整理",
                    description="把主回复再整理成一句话",
                    event="after_assistant_response",
                    action={
                        "action_type": "agent",
                        "agent_id": created_agent.id,
                    },
                ),
                owner_id=owner.id,
            )
            updated_hook = await hook_service.update_user_hook(
                session,
                created_hook.id,
                AssistantHookUpdateDTO(
                    name="回复前自动整理",
                    description="更新后的说明",
                    enabled=False,
                    event="before_assistant_response",
                    action={
                        "action_type": "agent",
                        "agent_id": created_agent.id,
                    },
                ),
                owner_id=owner.id,
            )
            hook_file = (
                tmp_path
                / "assistant-config"
                / "users"
                / str(owner.id)
                / "hooks"
                / created_hook.id
                / "HOOK.yaml"
            )
            listed_hooks = await hook_service.list_user_hooks(session, owner_id=owner.id)
            await hook_service.delete_user_hook(session, created_hook.id, owner_id=owner.id)

        assert created_hook.id.startswith("hook.user.")
        assert created_hook.action.action_type == "agent"
        assert created_hook.action.agent_id == created_agent.id
        assert created_hook.event == "after_assistant_response"
        assert updated_hook.enabled is False
        assert updated_hook.event == "before_assistant_response"
        assert listed_hooks[0].id == created_hook.id
        assert not hook_file.exists()
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_hook_service_supports_user_mcp_action(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    mcp_service = AssistantMcpService(
        config_loader=loader,
        project_service=create_project_service(),
        mcp_store=AssistantMcpFileStore(tmp_path / "assistant-config"),
    )
    hook_service = AssistantHookService(
        assistant_agent_service=AssistantAgentService(
            assistant_skill_service=AssistantSkillService(
                config_loader=loader,
                project_service=create_project_service(),
                skill_store=AssistantSkillFileStore(tmp_path / "assistant-config"),
            ),
            config_loader=loader,
            agent_store=AssistantAgentFileStore(tmp_path / "assistant-config"),
        ),
        assistant_mcp_service=mcp_service,
        config_loader=loader,
        hook_store=AssistantHookFileStore(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-hook-service-mcp")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
        async with async_session_factory() as session:
            created_mcp = await mcp_service.create_user_mcp_server(
                session,
                AssistantMcpCreateDTO(
                    name="新闻查询",
                    url="https://example.com/user-mcp",
                    headers={"X-Test": "demo"},
                ),
                owner_id=owner.id,
            )
            created_hook = await hook_service.create_user_hook(
                session,
                AssistantHookCreateDTO(
                    name="回复前查新闻",
                    event="before_assistant_response",
                    action={
                        "action_type": "mcp",
                        "server_id": created_mcp.id,
                        "tool_name": "search_news",
                        "arguments": {"limit": 3},
                        "input_mapping": {"query": "request.user_input"},
                    },
                ),
                owner_id=owner.id,
            )
            resolved = hook_service.resolve_hook(created_hook.id, owner_id=owner.id)

        assert created_hook.action.action_type == "mcp"
        assert created_hook.action.server_id == created_mcp.id
        assert resolved.action.action_type == "mcp"
        assert resolved.action.config["tool_name"] == "search_news"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def test_assistant_hook_create_dto_rejects_blank_name() -> None:
    with pytest.raises(ValidationError, match="Hook 名称不能为空"):
        AssistantHookCreateDTO(
            name="   ",
            event="after_assistant_response",
            action={"action_type": "agent", "agent_id": "agent.general_assistant"},
        )


def test_assistant_hook_document_rejects_non_agent_action(tmp_path) -> None:
    hook_file = tmp_path / "HOOK.yaml"
    hook_file.write_text(
        "\n".join(
            [
                "hook:",
                "  id: hook.user.reply-summary-a1b2c3",
                "  name: 回复后整理",
                "  enabled: true",
                "  trigger:",
                "    event: after_assistant_response",
                "    node_types: []",
                "  action:",
                "    type: webhook",
                "    config:",
                "      url: https://example.com",
                "",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="action type must be agent or mcp"):
        parse_hook_document(hook_file, hook_file.read_text(encoding="utf-8"))
