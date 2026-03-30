from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.assistant.service import (
    AssistantSkillCreateDTO,
    AssistantSkillService,
    AssistantTurnRequestDTO,
)
from app.modules.assistant.service.assistant_config_file_store import AssistantConfigFileStore
from app.modules.assistant.service.assistant_skill_support import parse_skill_markdown
from app.modules.assistant.service.assistant_rule_dto import AssistantRuleProfileUpdateDTO
from app.modules.assistant.service.dto import AssistantMessageDTO
from app.modules.assistant.service.preferences_dto import AssistantPreferencesUpdateDTO
from app.modules.assistant.service.preferences_service import AssistantPreferencesService
from app.modules.assistant.service.factory import create_assistant_rule_service
from app.modules.assistant.service.assistant_service import AssistantService
from app.modules.assistant.service.assistant_skill_file_store import AssistantSkillFileStore
from app.modules.config_registry import ConfigLoader
from app.modules.project.service import create_project_service
from app.shared.runtime import SkillTemplateRenderer
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError
from tests.unit.async_api_support import build_sqlite_session_factories, cleanup_sqlite_session_factories
from tests.unit.models.helpers import create_project, create_user
from tests.unit.test_assistant_service import (
    _FakeCredentialService,
    _FakeToolProvider,
    _build_config_root,
)


async def test_assistant_service_runs_user_skill(tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    tool_provider = _FakeToolProvider()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    skill_store = AssistantSkillFileStore(tmp_path / "assistant-config")
    skill_service = AssistantSkillService(
        config_loader=loader,
        project_service=create_project_service(),
        skill_store=skill_store,
    )
    service = AssistantService(
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
        build_sqlite_session_factories(tmp_path, name="assistant-user-skill")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
        async with async_session_factory() as session:
            created = await skill_service.create_user_skill(
                session,
                AssistantSkillCreateDTO(
                    name="温柔开题",
                    description="先给新手方向",
                    content=(
                        "请先给我 3 个故事方向，每个方向都短一点。\n"
                        "历史对话：{{ conversation_history }}\n"
                        "用户输入：{{ user_input }}"
                    ),
                ),
                owner_id=owner.id,
            )
            await service.assistant_preferences_service.update_preferences(
                session,
                owner.id,
                AssistantPreferencesUpdateDTO(
                    default_provider="openai",
                    default_model_name="gpt-4o-mini",
                ),
            )
            await service.assistant_rule_service.update_user_rules(
                session,
                payload=AssistantRuleProfileUpdateDTO(enabled=True, content="先给结论。"),
                owner_id=owner.id,
            )
            response = await service.turn(
                session,
                AssistantTurnRequestDTO(
                    skill_id=created.id,
                    messages=[AssistantMessageDTO(role="user", content="我想写校园成长故事")],
                ),
                owner_id=owner.id,
            )

        assert response.skill_id == created.id
        assert response.content.startswith("主回复：")
        assert "我想写校园成长故事" in tool_provider.prompts[0]
        assert "先给结论。" in (tool_provider.requests[0]["system_prompt"] or "")
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_assistant_skill_service_rejects_invalid_placeholder(tmp_path) -> None:
    loader = ConfigLoader(_build_config_root(tmp_path))
    skill_service = AssistantSkillService(
        config_loader=loader,
        project_service=create_project_service(),
        skill_store=AssistantSkillFileStore(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-user-skill-invalid")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
        async with async_session_factory() as session:
            with pytest.raises(BusinessRuleError, match="未声明的变量"):
                await skill_service.create_user_skill(
                    session,
                    AssistantSkillCreateDTO(
                        name="错误 Skill",
                        content="这里用了 {{ unknown_value }}",
                    ),
                    owner_id=owner.id,
                )
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def test_assistant_skill_create_dto_rejects_blank_name() -> None:
    with pytest.raises(ValidationError, match="Skill 名称不能为空"):
        AssistantSkillCreateDTO(
            name="   ",
            content="用户输入：{{ user_input }}",
        )


async def test_assistant_skill_service_creates_lists_and_resolves_project_skill(tmp_path) -> None:
    loader = ConfigLoader(_build_config_root(tmp_path))
    skill_service = AssistantSkillService(
        config_loader=loader,
        project_service=create_project_service(),
        skill_store=AssistantSkillFileStore(tmp_path / "assistant-config"),
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="assistant-project-skill")
    )

    try:
        with session_factory() as session:
            owner = create_user(session)
            project = create_project(session, owner=owner)
        async with async_session_factory() as session:
            created = await skill_service.create_project_skill(
                session,
                project.id,
                AssistantSkillCreateDTO(
                    name="项目开题",
                    content="请先按照项目口径回答。\n用户输入：{{ user_input }}",
                ),
                owner_id=owner.id,
            )
            listed = await skill_service.list_project_skills(
                session,
                project.id,
                owner_id=owner.id,
            )
            resolved = skill_service.resolve_skill(
                created.id,
                owner_id=owner.id,
                project_id=project.id,
            )

        assert created.id.startswith("skill.project.")
        assert listed[0].id == created.id
        assert "项目口径" in resolved.prompt
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


@pytest.mark.parametrize(
    ("frontmatter", "message"),
    [
        ('enabled: "false"', "field 'enabled' must be a boolean"),
        ("model:\n  max_tokens: true", "model max_tokens must be an integer"),
    ],
)
def test_assistant_skill_markdown_rejects_invalid_frontmatter_types(
    tmp_path,
    frontmatter: str,
    message: str,
) -> None:
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(
        "\n".join(
            [
                "---",
                "id: skill.user.story-helper-a1b2c3",
                "name: 温柔开题",
                frontmatter,
                "---",
                "",
                "用户输入：{{ user_input }}",
                "",
            ],
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match=message):
        parse_skill_markdown(skill_file, skill_file.read_text(encoding="utf-8"))
