from __future__ import annotations

import asyncio

import pytest

from app.modules.config_registry.schemas.config_schemas import SkillConfig, WorkflowConfig
from app.modules.content.models import ContentVersion
from app.modules.content.service import StoryAssetGenerateDTO, create_story_asset_generation_service
from app.modules.credential.infrastructure import CredentialCrypto
from app.modules.credential.models import ModelCredential
from app.shared.runtime import ToolProvider
from app.shared.runtime.errors import BusinessRuleError
from tests.unit.async_service_support import async_db
from tests.unit.models.helpers import (
    create_content,
    create_content_version,
    create_project,
    create_template,
    create_user,
    ready_project_setting,
)

TEST_MASTER_KEY = "credential-master-key-for-generation-tests"


class FakeToolProvider(ToolProvider):
    def __init__(self, *responses: str) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []

    async def execute(self, tool_name: str, params: dict) -> dict:
        assert tool_name == "llm.generate"
        self.prompts.append(params["prompt"])
        return {
            "content": self.responses.pop(0),
            "input_tokens": 12,
            "output_tokens": 34,
            "total_tokens": 46,
        }

    def list_tools(self) -> list[str]:
        return ["llm.generate"]


class StubConfigLoader:
    def __init__(self) -> None:
        self.workflow = WorkflowConfig.model_validate(
            {
                "id": "workflow.story_asset.mapping",
                "name": "映射测试工作流",
                "version": "1.0.0",
                "mode": "manual",
                "nodes": [
                    {
                        "id": "outline",
                        "name": "生成大纲",
                        "type": "generate",
                        "depends_on": [],
                        "skill": "skill.outline.mapping",
                    }
                ],
            }
        )
        self.skill = SkillConfig.model_validate(
            {
                "id": "skill.outline.mapping",
                "name": "映射测试技能",
                "version": "1.0.0",
                "description": "验证 direct/full-context 变量映射",
                "category": "outline",
                "prompt": "【题材】{{ genre }}\n【目标字数】{{ target_words }}\n【完整设定】{{ project_setting }}",
                "variables": {
                    "genre": {"type": "string", "required": True},
                    "target_words": {"type": "string", "required": True},
                    "project_setting": {"type": "string", "required": True},
                },
                "model": {
                    "provider": "anthropic",
                    "name": "claude-sonnet-4-20250514",
                },
            }
        )

    def load_workflow(self, workflow_id: str) -> WorkflowConfig:
        assert workflow_id == "workflow.story_asset.mapping"
        return self.workflow

    def load_skill(self, skill_id: str) -> SkillConfig:
        assert skill_id == "skill.outline.mapping"
        return self.skill

    def validate_skill_input(self, skill: SkillConfig, inputs: dict[str, str]) -> None:
        assert skill.id == self.skill.id
        assert inputs["target_words"] == "800000"
        assert '"genre": "玄幻"' in inputs["project_setting"]


def test_generate_outline_uses_template_workflow_and_saves_ai_draft(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    owner = create_user(db)
    template = create_template(db)
    project = create_project(
        db,
        owner=owner,
        template_id=template.id,
        project_setting=ready_project_setting(),
    )
    _create_anthropic_credential(db, owner.id)
    tool_provider = FakeToolProvider("玄幻大纲：主角入宗，卷一逃亡，终局复仇。")
    service = create_story_asset_generation_service(tool_provider=tool_provider)

    result = asyncio.run(
        service.generate_asset(
            async_db(db),
            project.id,
            "outline",
            StoryAssetGenerateDTO(),
            owner_id=owner.id,
        )
    )

    current = db.query(ContentVersion).filter(ContentVersion.content_id == result.content_id).one()
    assert result.title == "大纲"
    assert result.status == "draft"
    assert result.content_text == "玄幻大纲：主角入宗，卷一逃亡，终局复仇。"
    assert result.impact.has_impact is False
    assert current.created_by == "ai_assist"
    assert current.change_source == "ai_generate"
    assert "【题材】玄幻" in tool_provider.prompts[0]
    assert "[主角]" in tool_provider.prompts[0]
    assert "姓名：林渊" in tool_provider.prompts[0]
    assert "身份：弃徒" in tool_provider.prompts[0]
    assert "时代基线：宗门割据时代" in tool_provider.prompts[0]


def test_generate_opening_plan_requires_approved_outline(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    owner = create_user(db)
    template = create_template(db)
    project = create_project(
        db,
        owner=owner,
        template_id=template.id,
        project_setting=ready_project_setting(),
    )
    _create_anthropic_credential(db, owner.id)
    service = create_story_asset_generation_service(tool_provider=FakeToolProvider("不会执行"))

    with pytest.raises(BusinessRuleError, match="outline 必须先确认后才能继续"):
        asyncio.run(
            service.generate_asset(
                async_db(db),
                project.id,
                "opening_plan",
                StoryAssetGenerateDTO(),
                owner_id=owner.id,
            )
        )


def test_generate_opening_plan_supports_explicit_workflow_id(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    owner = create_user(db)
    project = create_project(
        db,
        owner=owner,
        project_setting=ready_project_setting(),
    )
    outline = create_content(
        db,
        project=project,
        content_type="outline",
        chapter_number=None,
        title="自定义大纲",
        status="approved",
    )
    create_content_version(db, content=outline, version_number=1, content_text="已确认大纲内容")
    _create_anthropic_credential(db, owner.id)
    tool_provider = FakeToolProvider("开篇设计：前三章先立钩子，再压迫主角。")
    service = create_story_asset_generation_service(tool_provider=tool_provider)

    result = asyncio.run(
        service.generate_asset(
            async_db(db),
            project.id,
            "opening_plan",
            StoryAssetGenerateDTO(workflow_id="workflow.xuanhuan_manual"),
            owner_id=owner.id,
        )
    )

    assert result.title == "开篇设计"
    assert result.version_number == 1
    assert result.content_text == "开篇设计：前三章先立钩子，再压迫主角。"
    assert result.impact.has_impact is False
    assert "【故事大纲】" in tool_provider.prompts[0]
    assert "已确认大纲内容" in tool_provider.prompts[0]
    assert "【人物设定】" in tool_provider.prompts[0]
    assert "姓名：林渊" in tool_provider.prompts[0]


def test_generate_outline_supports_direct_and_full_context_setting_mapping(db, monkeypatch) -> None:
    monkeypatch.setenv("EASYSTORY_CREDENTIAL_MASTER_KEY", TEST_MASTER_KEY)
    owner = create_user(db)
    template = create_template(db, config={"workflow_id": "workflow.story_asset.mapping"})
    project = create_project(
        db,
        owner=owner,
        template_id=template.id,
        project_setting=ready_project_setting(),
    )
    _create_anthropic_credential(db, owner.id)
    tool_provider = FakeToolProvider("映射测试大纲。")
    service = create_story_asset_generation_service(
        config_loader=StubConfigLoader(),
        tool_provider=tool_provider,
    )

    result = asyncio.run(
        service.generate_asset(
            async_db(db),
            project.id,
            "outline",
            StoryAssetGenerateDTO(),
            owner_id=owner.id,
        )
    )

    assert result.content_text == "映射测试大纲。"
    assert "【目标字数】800000" in tool_provider.prompts[0]
    assert '"target_words": 800000' in tool_provider.prompts[0]


def _create_anthropic_credential(db, owner_id):
    crypto = CredentialCrypto()
    credential = ModelCredential(
        owner_type="user",
        owner_id=owner_id,
        provider="anthropic",
        display_name="Anthropic",
        encrypted_key=crypto.encrypt("sk-anthropic-test"),
        is_active=True,
    )
    db.add(credential)
    db.commit()
    return credential
