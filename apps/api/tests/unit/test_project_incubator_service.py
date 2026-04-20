from __future__ import annotations

import pytest
from sqlalchemy import select

from app.modules.content.models import Content
from app.modules.credential.infrastructure import CredentialCrypto
from app.modules.credential.models import ModelCredential
from app.modules.project.service import (
    ProjectIncubatorAnswerDTO,
    ProjectIncubatorConversationDraftRequestDTO,
    ProjectIncubatorCreateRequestDTO,
    ProjectIncubatorDraftRequestDTO,
    create_project_incubator_service,
)
from app.shared.runtime.llm.llm_protocol_types import HttpJsonResponse
from app.shared.runtime.llm.llm_tool_provider import LLMToolProvider
from app.shared.runtime.tool_provider import ToolProvider
from app.modules.template.models import Template
from app.modules.template.service import (
    create_builtin_template_sync_service,
    create_template_query_service,
)
from app.shared.runtime.errors import BusinessRuleError
from tests.unit.async_api_support import (
    build_sqlite_session_factories,
    cleanup_sqlite_session_factories,
)
from tests.unit.models.helpers import create_user
from tests.unit.models.helpers import ready_project_setting

TEST_MASTER_KEY = "credential-master-key-for-project-incubator-tests"


class FakeConversationToolProvider(ToolProvider):
    def __init__(self, response) -> None:
        self.response = response
        self.prompts: list[str] = []
        self.params: list[dict] = []

    async def execute(self, tool_name: str, params: dict) -> dict:
        assert tool_name == "llm.generate"
        self.prompts.append(params["prompt"])
        self.params.append(params)
        return {
            "content": self.response,
            "input_tokens": 12,
            "output_tokens": 34,
            "total_tokens": 46,
        }

    def list_tools(self) -> list[str]:
        return ["llm.generate"]


async def test_project_incubator_service_builds_draft_from_builtin_template(tmp_path) -> None:
    sync_service = create_builtin_template_sync_service()
    query_service = create_template_query_service()
    incubator_service = create_project_incubator_service()
    _session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-incubator-service")
    )

    try:
        async with async_session_factory() as session:
            await sync_service.sync_builtin_templates(session)
            template_id = (await query_service.list_templates(session))[0].id
            draft = await incubator_service.build_draft(
                session,
                ProjectIncubatorDraftRequestDTO(
                    template_id=template_id,
                    answers=[
                        ProjectIncubatorAnswerDTO(
                            variable="protagonist",
                            value="宗门弃徒",
                        ),
                        ProjectIncubatorAnswerDTO(
                            variable="world_setting",
                            value="灵气衰退后的修真界",
                        ),
                        ProjectIncubatorAnswerDTO(
                            variable="core_conflict",
                            value="主角被追杀后试图重返宗门",
                        ),
                    ],
                ),
            )

        assert draft.template.name == "玄幻小说模板"
        assert draft.project_setting.genre == "玄幻"
        assert draft.project_setting.protagonist is not None
        assert draft.project_setting.protagonist.identity == "宗门弃徒"
        assert draft.project_setting.world_setting is not None
        assert draft.project_setting.world_setting.era_baseline == "灵气衰退后的修真界"
        assert draft.project_setting.core_conflict == "主角被追杀后试图重返宗门"
        assert draft.setting_completeness.status == "warning"
        assert [item.field for item in draft.setting_completeness.issues] == [
            "protagonist.goal",
            "tone",
            "scale",
        ]
        assert [item.field_path for item in draft.applied_answers] == [
            "protagonist.identity",
            "world_setting.era_baseline",
            "core_conflict",
        ]
        assert draft.unmapped_answers == []
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_incubator_service_reports_unmapped_supported_gap(tmp_path) -> None:
    incubator_service = create_project_incubator_service()
    _session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-incubator-unmapped")
    )

    try:
        async with async_session_factory() as session:
            session.add(_custom_template("映射缺口模板", "nickname"))
            await session.commit()
            template_id = await _load_template_id(session, "映射缺口模板")
            draft = await incubator_service.build_draft(
                session,
                ProjectIncubatorDraftRequestDTO(
                    template_id=template_id,
                    answers=[ProjectIncubatorAnswerDTO(variable="nickname", value="阿渊")],
                ),
            )

        assert draft.project_setting.genre == "科幻"
        assert draft.setting_completeness.status == "warning"
        assert draft.applied_answers == []
        assert [(item.variable, item.reason) for item in draft.unmapped_answers] == [
            ("nickname", "unsupported_variable")
        ]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_incubator_service_maps_legacy_conflict_variable(tmp_path) -> None:
    incubator_service = create_project_incubator_service()
    _session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-incubator-conflict")
    )

    try:
        async with async_session_factory() as session:
            session.add(_custom_template("旧冲突变量模板", "conflict"))
            await session.commit()
            template_id = await _load_template_id(session, "旧冲突变量模板")
            draft = await incubator_service.build_draft(
                session,
                ProjectIncubatorDraftRequestDTO(
                    template_id=template_id,
                    answers=[
                        ProjectIncubatorAnswerDTO(
                            variable="conflict",
                            value="主角必须在宗门压制中夺回成长机会",
                        )
                    ],
                ),
            )

        assert draft.project_setting.core_conflict == "主角必须在宗门压制中夺回成长机会"
        assert [(item.variable, item.field_path) for item in draft.applied_answers] == [
            ("core_conflict", "core_conflict")
        ]
        assert draft.unmapped_answers == []
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_incubator_service_creates_project_from_builtin_template(tmp_path) -> None:
    sync_service = create_builtin_template_sync_service()
    query_service = create_template_query_service()
    incubator_service = create_project_incubator_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-incubator-create")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id

        async with async_session_factory() as session:
            await sync_service.sync_builtin_templates(session)
            template_id = (await query_service.list_templates(session))[0].id
            created = await incubator_service.create_project(
                session,
                ProjectIncubatorCreateRequestDTO(
                    name="模板开局项目",
                    template_id=template_id,
                    answers=[
                        ProjectIncubatorAnswerDTO(
                            variable="protagonist",
                            value="宗门弃徒",
                        ),
                        ProjectIncubatorAnswerDTO(
                            variable="world_setting",
                            value="灵气衰退后的修真界",
                        ),
                        ProjectIncubatorAnswerDTO(
                            variable="core_conflict",
                            value="主角被追杀后试图重返宗门",
                        ),
                    ],
                    allow_system_credential_pool=True,
                ),
                owner_id=owner_id,
            )

            story_assets = (
                await session.scalars(
                    select(Content)
                    .where(Content.project_id == created.project.id)
                    .order_by(Content.content_type.asc())
                )
            ).all()

        assert created.project.name == "模板开局项目"
        assert created.project.template_id == template_id
        assert created.project.allow_system_credential_pool is True
        assert created.project.project_setting is not None
        assert created.project.project_setting.genre == "玄幻"
        assert created.project.project_setting.core_conflict == "主角被追杀后试图重返宗门"
        assert created.setting_completeness.status == "warning"
        assert [item.field for item in created.setting_completeness.issues] == [
            "protagonist.goal",
            "tone",
            "scale",
        ]
        assert [item.field_path for item in created.applied_answers] == [
            "protagonist.identity",
            "world_setting.era_baseline",
            "core_conflict",
        ]
        assert created.unmapped_answers == []
        assert [asset.content_type for asset in story_assets] == ["opening_plan", "outline"]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_incubator_service_creates_project_and_preserves_unmapped_answers(
    tmp_path,
) -> None:
    incubator_service = create_project_incubator_service()
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-incubator-create-unmapped")
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id

        async with async_session_factory() as session:
            session.add(_custom_template("一键创建映射缺口模板", "nickname"))
            await session.commit()
            template_id = await _load_template_id(session, "一键创建映射缺口模板")
            created = await incubator_service.create_project(
                session,
                ProjectIncubatorCreateRequestDTO(
                    name="映射缺口项目",
                    template_id=template_id,
                    answers=[ProjectIncubatorAnswerDTO(variable="nickname", value="阿渊")],
                ),
                owner_id=owner_id,
            )

        assert created.project.name == "映射缺口项目"
        assert created.project.project_setting is not None
        assert created.project.project_setting.genre == "科幻"
        assert created.setting_completeness.status == "warning"
        assert created.applied_answers == []
        assert [(item.variable, item.reason) for item in created.unmapped_answers] == [
            ("nickname", "unsupported_variable")
        ]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_incubator_service_reports_warning_when_optional_fields_missing(
    tmp_path,
) -> None:
    incubator_service = create_project_incubator_service()
    _session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-incubator-warning")
    )

    try:
        async with async_session_factory() as session:
            session.add(
                _custom_template_with_variables(
                    "完整必填模板",
                    [
                        "protagonist_identity",
                        "protagonist_goal",
                        "world_setting",
                        "core_conflict",
                    ],
                )
            )
            await session.commit()
            template_id = await _load_template_id(session, "完整必填模板")
            draft = await incubator_service.build_draft(
                session,
                ProjectIncubatorDraftRequestDTO(
                    template_id=template_id,
                    answers=[
                        ProjectIncubatorAnswerDTO(
                            variable="protagonist_identity",
                            value="宗门弃徒",
                        ),
                        ProjectIncubatorAnswerDTO(
                            variable="protagonist_goal",
                            value="重返内门",
                        ),
                        ProjectIncubatorAnswerDTO(
                            variable="world_setting",
                            value="灵气衰退后的修真界",
                        ),
                        ProjectIncubatorAnswerDTO(
                            variable="core_conflict",
                            value="主角被追杀后试图重返宗门",
                        ),
                    ],
                ),
            )

        assert draft.setting_completeness.status == "warning"
        assert [item.field for item in draft.setting_completeness.issues] == [
            "tone",
            "scale",
        ]
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_incubator_service_reports_ready_when_all_key_fields_present(
    tmp_path,
) -> None:
    incubator_service = create_project_incubator_service()
    _session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-incubator-ready")
    )

    try:
        async with async_session_factory() as session:
            session.add(
                _custom_template_with_variables(
                    "完整可启动模板",
                    [
                        "protagonist_identity",
                        "protagonist_goal",
                        "world_setting",
                        "core_conflict",
                        "tone",
                        "target_words",
                    ],
                )
            )
            await session.commit()
            template_id = await _load_template_id(session, "完整可启动模板")
            draft = await incubator_service.build_draft(
                session,
                ProjectIncubatorDraftRequestDTO(
                    template_id=template_id,
                    answers=[
                        ProjectIncubatorAnswerDTO(
                            variable="protagonist_identity",
                            value="宗门弃徒",
                        ),
                        ProjectIncubatorAnswerDTO(
                            variable="protagonist_goal",
                            value="重返内门",
                        ),
                        ProjectIncubatorAnswerDTO(
                            variable="world_setting",
                            value="灵气衰退后的修真界",
                        ),
                        ProjectIncubatorAnswerDTO(
                            variable="core_conflict",
                            value="主角被追杀后试图重返宗门",
                        ),
                        ProjectIncubatorAnswerDTO(
                            variable="tone",
                            value="冷峻克制",
                        ),
                        ProjectIncubatorAnswerDTO(
                            variable="target_words",
                            value="800000",
                        ),
                    ],
                ),
            )

        assert draft.setting_completeness.status == "ready"
        assert draft.setting_completeness.issues == []
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_incubator_service_rejects_invalid_answer_shape(tmp_path) -> None:
    incubator_service = create_project_incubator_service()
    _session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-incubator-invalid")
    )

    try:
        async with async_session_factory() as session:
            session.add(_custom_template("数值模板", "target_words"))
            await session.commit()
            template_id = await _load_template_id(session, "数值模板")

            with pytest.raises(BusinessRuleError):
                await incubator_service.build_draft(
                    session,
                    ProjectIncubatorDraftRequestDTO(
                        template_id=template_id,
                        answers=[
                            ProjectIncubatorAnswerDTO(
                                variable="target_words",
                                value="很多很多字",
                            )
                        ],
                    ),
                )

            with pytest.raises(BusinessRuleError):
                await incubator_service.build_draft(
                    session,
                    ProjectIncubatorDraftRequestDTO(
                        template_id=template_id,
                        answers=[
                            ProjectIncubatorAnswerDTO(
                                variable="not_declared",
                                value="x",
                            )
                        ],
                    ),
                )
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_incubator_service_rejects_blank_answer_value(tmp_path) -> None:
    incubator_service = create_project_incubator_service()
    _session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-incubator-blank")
    )

    try:
        async with async_session_factory() as session:
            session.add(_custom_template("空白答案模板", "protagonist"))
            await session.commit()
            template_id = await _load_template_id(session, "空白答案模板")

            with pytest.raises(BusinessRuleError, match="值不能为空"):
                await incubator_service.build_draft(
                    session,
                    ProjectIncubatorDraftRequestDTO(
                        template_id=template_id,
                        answers=[ProjectIncubatorAnswerDTO(variable="protagonist", value="   ")],
                    ),
                )
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_incubator_service_builds_conversation_draft(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
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
    incubator_service = create_project_incubator_service(tool_provider=fake_provider)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(tmp_path, name="project-incubator-conversation")
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
                auth_strategy="custom_header",
                api_key_header_name="api-key",
                extra_headers={"HTTP-Referer": "https://story.example.com"},
            )

        async with async_session_factory() as session:
            draft = await incubator_service.build_conversation_draft(
                session,
                ProjectIncubatorConversationDraftRequestDTO(
                    conversation_text=(
                        "我想写一本玄幻修仙小说，主角是没落家族少年，"
                        "他要在宗门压制中夺回成长机会并为家族复仇。"
                    ),
                    provider="anthropic",
                ),
                owner_id=owner_id,
            )

        assert draft.project_setting.genre == "玄幻修仙"
        assert draft.project_setting.protagonist is not None
        assert draft.project_setting.protagonist.identity == "没落家族少年"
        assert draft.project_setting.protagonist.goal == "恢复天赋，为家族复仇"
        assert draft.project_setting.world_setting is not None
        assert draft.project_setting.world_setting.era_baseline == "宗门林立、强者为尊"
        assert draft.setting_completeness.status == "warning"
        assert [item.field for item in draft.setting_completeness.issues] == [
            "tone",
            "scale",
        ]
        assert draft.follow_up_questions == [
            "你希望整体基调或文风更偏什么感觉？",
            "这本书大概准备写多少字，或者规划多少章？",
        ]
        assert "只输出 JSON 对象本身" in fake_provider.prompts[0]
        assert fake_provider.params[0]["model"]["provider"] == "anthropic"
        assert fake_provider.params[0]["model"]["name"] == "claude-sonnet-4-20250514"
        assert fake_provider.params[0]["credential"]["auth_strategy"] == "custom_header"
        assert fake_provider.params[0]["credential"]["api_key_header_name"] == "api-key"
        assert fake_provider.params[0]["credential"]["extra_headers"] == {
            "HTTP-Referer": "https://story.example.com"
        }
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_incubator_service_rejects_invalid_conversation_output(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    incubator_service = create_project_incubator_service(
        tool_provider=FakeConversationToolProvider({"protagonist": "林渊"})
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(
            tmp_path,
            name="project-incubator-conversation-invalid",
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

        async with async_session_factory() as session:
            with pytest.raises(BusinessRuleError, match="ProjectSetting schema"):
                await incubator_service.build_conversation_draft(
                    session,
                    ProjectIncubatorConversationDraftRequestDTO(
                        conversation_text="我想写一个主角叫林渊的故事。",
                        provider="anthropic",
                    ),
                    owner_id=owner_id,
                )
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_incubator_service_rejects_blank_conversation_text(
    tmp_path,
) -> None:
    incubator_service = create_project_incubator_service(
        tool_provider=FakeConversationToolProvider({})
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(
            tmp_path,
            name="project-incubator-conversation-blank",
        )
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id

        async with async_session_factory() as session:
            with pytest.raises(BusinessRuleError, match="conversation_text cannot be blank"):
                await incubator_service.build_conversation_draft(
                    session,
                    ProjectIncubatorConversationDraftRequestDTO(
                        conversation_text="   ",
                        provider="openai",
                    ),
                    owner_id=owner_id,
                )
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_incubator_service_uses_explicit_model_name_override(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    fake_provider = FakeConversationToolProvider({"genre": "科幻"})
    incubator_service = create_project_incubator_service(tool_provider=fake_provider)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(
            tmp_path,
            name="project-incubator-conversation-model-override",
        )
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
            create_model_credential(
                session,
                owner_id,
                provider="openai",
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
            )

        async with async_session_factory() as session:
            await incubator_service.build_conversation_draft(
                session,
                ProjectIncubatorConversationDraftRequestDTO(
                    conversation_text="我想写一本科幻小说。",
                    provider="openai",
                    model_name="gpt-4.1",
                ),
                owner_id=owner_id,
            )

        assert fake_provider.params[0]["model"]["provider"] == "openai"
        assert fake_provider.params[0]["model"]["name"] == "gpt-4.1"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_incubator_service_merges_conversation_draft_with_base_setting(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    fake_provider = FakeConversationToolProvider(
        {
            "tone": "热血",
            "protagonist": {
                "identity": "背负旧债的宗门弃徒",
            },
        }
    )
    incubator_service = create_project_incubator_service(tool_provider=fake_provider)
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(
            tmp_path,
            name="project-incubator-conversation-merge-base",
        )
    )

    try:
        with session_factory() as session:
            owner_id = create_user(session).id
            create_model_credential(
                session,
                owner_id,
                provider="openai",
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
            )

        async with async_session_factory() as session:
            draft = await incubator_service.build_conversation_draft(
                session,
                ProjectIncubatorConversationDraftRequestDTO(
                    conversation_text="把主角身份改得更苦一点，整体更热血。",
                    provider="openai",
                    base_project_setting=ready_project_setting(),
                ),
                owner_id=owner_id,
            )

        assert draft.project_setting.genre == "玄幻"
        assert draft.project_setting.core_conflict == "主角在宗门追杀中求生"
        assert draft.project_setting.tone == "热血"
        assert draft.project_setting.protagonist is not None
        assert draft.project_setting.protagonist.identity == "背负旧债的宗门弃徒"
        assert draft.project_setting.protagonist.goal == "重返内门"
        assert draft.project_setting.world_setting is not None
        assert draft.project_setting.world_setting.era_baseline == "宗门割据时代"
        assert draft.setting_completeness.status == "ready"
        assert draft.follow_up_questions == []
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


async def test_project_incubator_service_accepts_parseable_truncated_json_object(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)

    async def request_sender(_request):
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "content": [
                    {
                        "type": "text",
                        "text": (
                            '{"genre":"玄幻修仙","core_conflict":"主角必须在宗门压制中夺回成长机会",'
                            '"protagonist":{"identity":"没落家族少年","goal":"恢复天赋，为家族复仇"},'
                            '"world_setting":{"era_baseline":"宗门林立、强者为尊"}}'
                        ),
                    }
                ],
                "stop_reason": "max_tokens",
                "usage": {"input_tokens": 10, "output_tokens": 20},
            },
            text="",
        )

    incubator_service = create_project_incubator_service(
        tool_provider=LLMToolProvider(request_sender=request_sender)
    )
    session_factory, async_session_factory, engine, async_engine, database_path = (
        build_sqlite_session_factories(
            tmp_path,
            name="project-incubator-conversation-truncated-json",
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

        async with async_session_factory() as session:
            draft = await incubator_service.build_conversation_draft(
                session,
                ProjectIncubatorConversationDraftRequestDTO(
                    conversation_text="我想写一本玄幻修仙小说。",
                    provider="anthropic",
                ),
                owner_id=owner_id,
            )

        assert draft.project_setting.genre == "玄幻修仙"
        assert draft.project_setting.core_conflict == "主角必须在宗门压制中夺回成长机会"
        assert draft.project_setting.protagonist is not None
        assert draft.project_setting.protagonist.identity == "没落家族少年"
    finally:
        await cleanup_sqlite_session_factories(engine, async_engine, database_path)


def _custom_template(name: str, variable: str) -> Template:
    return _custom_template_with_variables(name, [variable])


def _custom_template_with_variables(name: str, variables: list[str]) -> Template:
    return Template(
        name=name,
        genre="科幻",
        config={
            "workflow_id": "workflow.xuanhuan_manual",
            "guided_questions": [
                {
                    "question": f"{variable}?",
                    "variable": variable,
                }
                for variable in variables
            ],
        },
        is_builtin=False,
    )


async def _load_template_id(session, name: str):
    templates = await create_template_query_service().list_templates(session)
    return next(template.id for template in templates if template.name == name)


def create_model_credential(
    session,
    owner_id,
    *,
    provider: str,
    api_dialect: str,
    default_model: str,
    auth_strategy: str | None = None,
    api_key_header_name: str | None = None,
    extra_headers: dict[str, str] | None = None,
):
    crypto = CredentialCrypto()
    credential = ModelCredential(
        owner_type="user",
        owner_id=owner_id,
        provider=provider,
        api_dialect=api_dialect,
        display_name=provider.title(),
        encrypted_key=crypto.encrypt(f"sk-{provider}-test"),
        default_model=default_model,
        auth_strategy=auth_strategy,
        api_key_header_name=api_key_header_name,
        extra_headers=extra_headers,
        is_active=True,
    )
    session.add(credential)
    session.commit()
    return credential
