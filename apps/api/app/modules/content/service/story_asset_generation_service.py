from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from typing import Any

from jinja2.exceptions import SecurityError, UndefinedError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.schemas.config_schemas import ModelConfig, NodeConfig, SkillConfig, WorkflowConfig
from app.modules.credential.service import CredentialService
from app.modules.credential.service.credential_connection_support import build_runtime_credential_payload
from app.modules.project.models import Project
from app.modules.project.schemas import ProjectSettingProjectionError, resolve_setting_variable
from app.modules.project.service import ProjectService
from app.shared.runtime import SkillTemplateRenderer, ToolProvider
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError
from app.shared.runtime.llm.llm_tool_provider import LLM_GENERATE_TOOL

from .chapter_store import require_approved_asset
from .dto import AssetType, StoryAssetGenerateDTO, StoryAssetMutationDTO, StoryAssetSaveDTO
from .story_asset_service import PREPARATION_ASSET_TITLES, StoryAssetService

GENERATED_VERSION_CREATED_BY = "ai_assist"
GENERATED_VERSION_CHANGE_SOURCE = "ai_generate"
GENERATED_CHANGE_SUMMARIES: dict[AssetType, str] = {
    "outline": "AI 生成大纲草稿",
    "opening_plan": "AI 生成开篇设计草稿",
}


class StoryAssetGenerationService:
    def __init__(
        self,
        *,
        project_service: ProjectService,
        story_asset_service: StoryAssetService,
        config_loader: ConfigLoader,
        credential_service_factory: Callable[[], CredentialService],
        tool_provider: ToolProvider,
        template_renderer: SkillTemplateRenderer,
    ) -> None:
        self.project_service = project_service
        self.story_asset_service = story_asset_service
        self.config_loader = config_loader
        self.credential_service_factory = credential_service_factory
        self.tool_provider = tool_provider
        self.template_renderer = template_renderer
        self._credential_service: CredentialService | None = None

    async def generate_asset(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        asset_type: AssetType,
        payload: StoryAssetGenerateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> StoryAssetMutationDTO:
        project = await self.project_service.require_project(
            db,
            project_id,
            owner_id=owner_id,
            load_contents=True,
            load_template=True,
        )
        self.project_service.ensure_setting_allows_preparation(project)
        await self._ensure_asset_dependencies_ready(db, project.id, asset_type)
        workflow_config = self._resolve_workflow_config(project, payload.workflow_id)
        node = self._require_generation_node(workflow_config, asset_type)
        skill = self.config_loader.load_skill(node.skill or "")
        model = self._resolve_model(workflow_config, node, skill)
        prompt = await self._build_prompt(db, project, skill)
        generated_text = await self._generate_text(
            db,
            project,
            model,
            prompt,
            owner_id=owner_id,
        )
        return await self.story_asset_service.save_asset_draft(
            db,
            project_id,
            asset_type,
            StoryAssetSaveDTO(
                title=self._resolve_asset_title(project, asset_type),
                content_text=generated_text,
                created_by=GENERATED_VERSION_CREATED_BY,
                change_source=GENERATED_VERSION_CHANGE_SOURCE,
                change_summary=GENERATED_CHANGE_SUMMARIES[asset_type],
            ),
            owner_id=owner_id,
        )

    async def _ensure_asset_dependencies_ready(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        asset_type: AssetType,
    ) -> None:
        if asset_type == "opening_plan":
            await require_approved_asset(db, project_id, "outline")

    def _resolve_workflow_config(
        self,
        project: Project,
        requested_workflow_id: str | None,
    ) -> WorkflowConfig:
        workflow_id = self._normalize_workflow_id(requested_workflow_id)
        if workflow_id is None:
            workflow_id = self._extract_template_workflow_id(project)
        if workflow_id is None:
            raise BusinessRuleError("项目未绑定默认工作流，请显式指定 workflow_id")
        return self.config_loader.load_workflow(workflow_id)

    def _normalize_workflow_id(self, workflow_id: str | None) -> str | None:
        if workflow_id is None:
            return None
        normalized = workflow_id.strip()
        if not normalized:
            raise BusinessRuleError("workflow_id cannot be blank")
        return normalized

    def _extract_template_workflow_id(self, project: Project) -> str | None:
        template = project.template
        if template is None or template.config is None:
            return None
        workflow_id = template.config.get("workflow_id")
        if workflow_id is None:
            return None
        if not isinstance(workflow_id, str) or not workflow_id.strip():
            raise ConfigurationError("Template.config.workflow_id must be a non-empty string")
        return workflow_id.strip()

    def _require_generation_node(
        self,
        workflow_config: WorkflowConfig,
        asset_type: AssetType,
    ) -> NodeConfig:
        for node in workflow_config.nodes:
            if node.id != asset_type:
                continue
            if node.node_type != "generate":
                raise ConfigurationError(f"Node {node.id} does not support generation")
            if not node.skill:
                raise ConfigurationError(f"Node {node.id} is missing skill id")
            return node
        raise ConfigurationError(f"Workflow {workflow_config.id} is missing node: {asset_type}")

    def _resolve_model(
        self,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        skill: SkillConfig,
    ) -> ModelConfig:
        model = node.model or skill.model or workflow_config.model
        if model is None or not model.provider:
            raise ConfigurationError(f"Node {node.id} is missing executable model configuration")
        return model

    async def _build_prompt(
        self,
        db: AsyncSession,
        project: Project,
        skill: SkillConfig,
    ) -> str:
        variables = await self._resolve_prompt_variables(db, project, skill)
        try:
            return self.template_renderer.render(skill.prompt, variables)
        except (SecurityError, UndefinedError) as exc:
            raise ConfigurationError(f"Story asset generation prompt render failed: {exc}") from exc

    async def _resolve_prompt_variables(
        self,
        db: AsyncSession,
        project: Project,
        skill: SkillConfig,
    ) -> dict[str, str]:
        declared = skill.variables or skill.inputs
        variables = {
            name: await self._resolve_declared_variable(db, project, name)
            for name in declared
        }
        missing = [
            name
            for name, schema in declared.items()
            if getattr(schema, "required", False) and not variables.get(name)
        ]
        if missing:
            raise BusinessRuleError(f"缺少 Skill 必填变量: {', '.join(sorted(missing))}")
        self.config_loader.validate_skill_input(skill, variables)
        return {name: value for name, value in variables.items() if value}

    async def _resolve_declared_variable(
        self,
        db: AsyncSession,
        project: Project,
        name: str,
    ) -> str:
        if name == "outline":
            return await self._load_asset_text(db, project.id, "outline")
        if name == "opening_plan":
            return await self._load_asset_text(db, project.id, "opening_plan")
        return self._stringify(self._resolve_setting_variable(project.project_setting, name))

    def _resolve_setting_variable(
        self,
        setting_payload: dict[str, Any] | None,
        variable_name: str,
    ) -> Any:
        if setting_payload is None:
            return None
        try:
            return resolve_setting_variable(setting_payload, variable_name)
        except ProjectSettingProjectionError as exc:
            raise BusinessRuleError(f"{variable_name} 设定变量无效") from exc

    async def _load_asset_text(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        asset_type: AssetType,
    ) -> str:
        asset = await self.story_asset_service.get_asset(db, project_id, asset_type)
        return asset.content_text

    async def _generate_text(
        self,
        db: AsyncSession,
        project: Project,
        model: ModelConfig,
        prompt: str,
        *,
        owner_id: uuid.UUID,
    ) -> str:
        credential_service = self._resolve_credential_service()
        credential = await credential_service.resolve_active_credential(
            db,
            provider=model.provider or "",
            user_id=owner_id,
            project_id=project.id,
        )
        raw_output = await self.tool_provider.execute(
            LLM_GENERATE_TOOL,
            {
                "prompt": prompt,
                "system_prompt": None,
                "model": model.model_dump(mode="json", exclude_none=True),
                "credential": build_runtime_credential_payload(
                    credential,
                    decrypt_api_key=credential_service.crypto.decrypt,
                ),
                "response_format": "text",
            },
        )
        content = raw_output.get("content")
        if not isinstance(content, str):
            raise ConfigurationError("Story asset generate output must be plain text")
        normalized = content.strip()
        if not normalized:
            raise BusinessRuleError("生成结果为空，无法保存")
        return normalized

    def _resolve_credential_service(self) -> CredentialService:
        if self._credential_service is None:
            self._credential_service = self.credential_service_factory()
        return self._credential_service

    def _resolve_asset_title(
        self,
        project: Project,
        asset_type: AssetType,
    ) -> str:
        for content in project.contents:
            if content.content_type == asset_type and content.title.strip():
                return content.title
        return PREPARATION_ASSET_TITLES[asset_type]

    def _stringify(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, indent=2)
        return str(value)
