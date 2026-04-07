from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.project.service import ProjectService

from ..assistant_config_file_store import AssistantConfigFileStore
from .assistant_rule_dto import AssistantRuleBundleDTO, AssistantRuleProfileDTO, AssistantRuleProfileUpdateDTO
from ..factory_support import build_default_assistant_config_store


class AssistantRuleService:
    def __init__(
        self,
        project_service: ProjectService,
        *,
        config_store: AssistantConfigFileStore | None = None,
    ) -> None:
        self.project_service = project_service
        self.config_store = config_store or build_default_assistant_config_store()

    async def get_user_rules(
        self,
        db: AsyncSession,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantRuleProfileDTO:
        del db
        return self.config_store.load_user_rule(owner_id)

    async def update_user_rules(
        self,
        db: AsyncSession,
        payload: AssistantRuleProfileUpdateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantRuleProfileDTO:
        del db
        return self.config_store.save_user_rule(owner_id, payload)

    async def get_project_rules(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantRuleProfileDTO:
        project = await self.project_service.require_project(db, project_id, owner_id=owner_id)
        return self.config_store.load_project_rule(project.id)

    async def update_project_rules(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        payload: AssistantRuleProfileUpdateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantRuleProfileDTO:
        project = await self.project_service.require_project(db, project_id, owner_id=owner_id)
        return self.config_store.save_project_rule(project.id, payload)

    async def build_rule_bundle(
        self,
        db: AsyncSession,
        *,
        owner_id: uuid.UUID,
        project_id: uuid.UUID | None,
    ) -> AssistantRuleBundleDTO:
        user_rules = await self.get_user_rules(db, owner_id=owner_id)
        project_rules = None
        if project_id is not None:
            project_rules = await self.get_project_rules(db, project_id, owner_id=owner_id)
        return AssistantRuleBundleDTO(
            user_content=_resolve_runtime_content(user_rules),
            project_content=_resolve_runtime_content(project_rules),
        )


def _resolve_runtime_content(profile: AssistantRuleProfileDTO | None) -> str | None:
    if profile is None or not profile.enabled:
        return None
    content = profile.content.strip()
    return content or None
