from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.assistant.service import (
    AssistantAgentCreateDTO,
    AssistantAgentService,
    AssistantSkillCreateDTO,
    AssistantSkillService,
    AssistantTurnRequestDTO,
)
from app.modules.assistant.service.agents.assistant_agent_file_store import AssistantAgentFileStore
from app.modules.assistant.service.agents.assistant_agent_support import parse_agent_markdown
from app.modules.assistant.service.assistant_config_file_store import AssistantConfigFileStore
from app.modules.assistant.service.rules.assistant_rule_dto import AssistantRuleProfileUpdateDTO
from app.modules.assistant.service.skills.assistant_skill_file_store import (
    AssistantSkillFileStore,
)
from app.modules.assistant.service.assistant_service import AssistantService
from app.modules.assistant.service.dto import AssistantMessageDTO
from app.modules.assistant.service.factory import create_assistant_rule_service
from app.modules.assistant.service.preferences.preferences_dto import (
    AssistantPreferencesUpdateDTO,
)
from app.modules.assistant.service.preferences.preferences_service import (
    AssistantPreferencesService,
)
from app.modules.config_registry import ConfigLoader
from app.modules.project.service import create_project_service
from app.shared.runtime.template_renderer import SkillTemplateRenderer
from app.shared.runtime.errors import ConfigurationError
from tests.unit.async_api_support import build_sqlite_session_factories, cleanup_sqlite_session_factories
from tests.unit.models.helpers import create_user
from tests.unit.test_assistant_service import (
    _FakeCredentialService,
    _FakeToolProvider,
    _build_config_root,
)


async def test_assistant_service_runs_user_agent_with_disabled_user_skill(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
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
    service = AssistantService(
        assistant_agent_service=agent_service,
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        assistant_preferences_service=AssistantPreferencesService(
            project_service=create_project_service(),
            config_store=assistant_store,
        ),
        assistant_skill_service=skill_service,
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=create_project_service(),
        tool_provider=tool_provider,
        template_renderer=SkillTemplateRenderer(),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-user-agent")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
        async with async_session_factory() as session:
            created_skill = await skill_service.create_user_skill(
                session,
                AssistantSkillCreateDTO(
                    name="隐藏聊天 Skill",
                    enabled=False,
                    content="请先给我 2 个故事方向。\n用户输入：{{ user_input }}",
                ),
                owner_id=owner.id,
            )
            created_agent = await agent_service.create_user_agent(
                session,
                AssistantAgentCreateDTO(
                    name="温柔陪跑",
                    description="更像陪聊型创作教练",
                    skill_id=created_skill.id,
                    system_prompt="先给结论，再用温和口吻陪用户收拢方向。",
                ),
                owner_id=owner.id,
            )
            await service.assistant_preferences_service.update_user_preferences(
                session,
                owner_id=owner.id,
                payload=AssistantPreferencesUpdateDTO(
                    default_provider="openai",
                    default_model_name="gpt-4o-mini",
                ),
            )
            await service.assistant_rule_service.update_user_rules(
                session,
                payload=AssistantRuleProfileUpdateDTO(enabled=True, content="不要像表单一样追问。"),
                owner_id=owner.id,
            )
            response = await service.turn(
                session,
                AssistantTurnRequestDTO(
                    conversation_id="conversation-agent-service",
                    client_turn_id="turn-agent-service-1",
                    agent_id=created_agent.id,
                    requested_write_scope="disabled",
                    messages=[AssistantMessageDTO(role="user", content="我想写一个轻松成长故事")],
                ),
                owner_id=owner.id,
            )

        assert response.agent_id == created_agent.id
        assert response.skill_id == created_skill.id
        assert response.content.startswith("主回复：")
        assert "我想写一个轻松成长故事" in tool_provider.prompts[0]
        assert "先给结论，再用温和口吻陪用户收拢方向。" in (tool_provider.requests[0]["system_prompt"] or "")
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def test_assistant_agent_create_dto_rejects_blank_name() -> None:
    with pytest.raises(ValidationError, match="Agent 名称不能为空"):
        AssistantAgentCreateDTO(
            name="   ",
            skill_id="skill.assistant.general_chat",
            system_prompt="请直接回答用户。",
        )


@pytest.mark.parametrize(
    ("frontmatter", "message"),
    [
        ('enabled: "false"', "field 'enabled' must be a boolean"),
        ("model:\n  max_tokens: true", "model max_tokens must be an integer"),
    ],
)
def test_assistant_agent_markdown_rejects_invalid_frontmatter_types(
    tmp_path,
    frontmatter: str,
    message: str,
) -> None:
    agent_file = tmp_path / "AGENT.md"
    agent_file.write_text(
        "\n".join(
            [
                "---",
                "id: agent.user.story-coach-a1b2c3",
                "name: 温柔陪跑",
                "skill_id: skill.assistant.general_chat",
                frontmatter,
                "---",
                "",
                "先给结论，再陪用户一点点收拢方向。",
                "",
            ],
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match=message):
        parse_agent_markdown(agent_file, agent_file.read_text(encoding="utf-8"))
