from __future__ import annotations

from collections.abc import Callable
import uuid
from typing import TYPE_CHECKING

from jinja2.exceptions import SecurityError, UndefinedError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.schemas.config_schemas import ModelConfig, SkillConfig
from app.modules.template.service import TemplateQueryService
from app.shared.runtime import SkillTemplateRenderer, ToolProvider
from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.llm_tool_provider import LLM_GENERATE_TOOL

from .dto import (
    ProjectCreateDTO,
    ProjectIncubatorConversationDraftDTO,
    ProjectIncubatorConversationDraftRequestDTO,
    ProjectIncubatorCreateRequestDTO,
    ProjectIncubatorCreateResultDTO,
    ProjectIncubatorDraftDTO,
    ProjectIncubatorDraftRequestDTO,
)
from .project_management_service import ProjectManagementService
from .project_incubator_support import (
    build_incubator_template_snapshot,
    build_project_setting_draft,
    build_setting_follow_up_questions,
    ensure_answers_match_template,
    normalize_conversation_text,
    normalize_requested_model_name,
    normalize_requested_provider,
    parse_project_setting_output,
    PROJECT_SETTING_CONVERSATION_SKILL_ID,
)
from .project_service_support import evaluate_project_setting
from app.modules.project.schemas import merge_project_setting

if TYPE_CHECKING:
    from app.modules.credential.service import CredentialService


class ProjectIncubatorService:
    def __init__(
        self,
        template_query_service: TemplateQueryService,
        project_management_service: ProjectManagementService,
        *,
        config_loader: ConfigLoader,
        credential_service_factory: Callable[[], CredentialService],
        tool_provider: ToolProvider,
        template_renderer: SkillTemplateRenderer,
    ) -> None:
        self.template_query_service = template_query_service
        self.project_management_service = project_management_service
        self.config_loader = config_loader
        self.credential_service_factory = credential_service_factory
        self.tool_provider = tool_provider
        self.template_renderer = template_renderer
        self._credential_service: CredentialService | None = None

    async def build_draft(
        self,
        db: AsyncSession,
        payload: ProjectIncubatorDraftRequestDTO,
    ) -> ProjectIncubatorDraftDTO:
        template = await self.template_query_service.get_template(db, payload.template_id)
        ensure_answers_match_template(template, payload.answers)
        project_setting, applied_answers, unmapped_answers = build_project_setting_draft(
            template,
            payload.answers,
        )
        return ProjectIncubatorDraftDTO(
            template=build_incubator_template_snapshot(template),
            project_setting=project_setting,
            setting_completeness=evaluate_project_setting(project_setting),
            applied_answers=applied_answers,
            unmapped_answers=unmapped_answers,
        )

    async def build_conversation_draft(
        self,
        db: AsyncSession,
        payload: ProjectIncubatorConversationDraftRequestDTO,
        *,
        owner_id: uuid.UUID,
    ) -> ProjectIncubatorConversationDraftDTO:
        skill = self.config_loader.load_skill(PROJECT_SETTING_CONVERSATION_SKILL_ID)
        prompt = self._build_conversation_prompt(
            skill,
            normalize_conversation_text(payload.conversation_text),
        )
        model = self._build_requested_model(
            skill,
            provider=normalize_requested_provider(payload.provider),
            model_name=normalize_requested_model_name(payload.model_name),
        )
        project_setting = await self._extract_project_setting(
            db,
            prompt,
            model,
            owner_id=owner_id,
        )
        if payload.base_project_setting is not None:
            project_setting = merge_project_setting(
                payload.base_project_setting,
                project_setting,
            )
        completeness = evaluate_project_setting(project_setting)
        return ProjectIncubatorConversationDraftDTO(
            project_setting=project_setting,
            setting_completeness=completeness,
            follow_up_questions=build_setting_follow_up_questions(completeness),
        )

    async def create_project(
        self,
        db: AsyncSession,
        payload: ProjectIncubatorCreateRequestDTO,
        *,
        owner_id,
    ) -> ProjectIncubatorCreateResultDTO:
        draft = await self.build_draft(
            db,
            ProjectIncubatorDraftRequestDTO(
                template_id=payload.template_id,
                answers=payload.answers,
            ),
        )
        project = await self.project_management_service.create_project(
            db,
            ProjectCreateDTO(
                name=payload.name,
                template_id=payload.template_id,
                project_setting=draft.project_setting,
                allow_system_credential_pool=payload.allow_system_credential_pool,
            ),
            owner_id=owner_id,
        )
        return ProjectIncubatorCreateResultDTO(
            project=project,
            setting_completeness=draft.setting_completeness,
            applied_answers=draft.applied_answers,
            unmapped_answers=draft.unmapped_answers,
        )

    def _build_conversation_prompt(
        self,
        skill: SkillConfig,
        conversation_text: str,
    ) -> str:
        variables = {"conversation_text": conversation_text}
        self.config_loader.validate_skill_input(skill, variables)
        try:
            return self.template_renderer.render(skill.prompt, variables)
        except (SecurityError, UndefinedError) as exc:
            raise ConfigurationError(
                f"Project incubator conversation prompt render failed: {exc}"
            ) from exc

    def _build_requested_model(
        self,
        skill: SkillConfig,
        *,
        provider: str,
        model_name: str | None,
    ) -> ModelConfig:
        base_model = skill.model.model_copy(deep=True) if skill.model is not None else ModelConfig()
        return base_model.model_copy(
            update={
                "provider": provider,
                "name": model_name,
            }
        )

    async def _extract_project_setting(
        self,
        db: AsyncSession,
        prompt: str,
        model: ModelConfig,
        *,
        owner_id: uuid.UUID,
    ):
        from app.modules.credential.service import build_runtime_credential_payload

        credential_service = self._resolve_credential_service()
        resolved = await credential_service.resolve_active_credential_model(
            db,
            provider=model.provider or "",
            requested_model_name=model.name,
            user_id=owner_id,
        )
        resolved_model = model.model_copy(update={"name": resolved.model_name})
        raw_output = await self.tool_provider.execute(
            LLM_GENERATE_TOOL,
            {
                "prompt": prompt,
                "system_prompt": None,
                "model": resolved_model.model_dump(mode="json", exclude_none=True),
                "credential": build_runtime_credential_payload(
                    resolved.credential,
                    decrypt_api_key=credential_service.crypto.decrypt,
                ),
                "response_format": "json_object",
            },
        )
        return parse_project_setting_output(raw_output.get("content"))

    def _resolve_credential_service(self) -> CredentialService:
        if self._credential_service is None:
            self._credential_service = self.credential_service_factory()
        return self._credential_service
