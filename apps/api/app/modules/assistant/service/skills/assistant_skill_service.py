from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry import ConfigLoader
from app.modules.project.service import ProjectService
from app.shared.runtime.errors import BusinessRuleError

from .assistant_skill_dto import (
    AssistantSkillCreateDTO,
    AssistantSkillDetailDTO,
    AssistantSkillSummaryDTO,
    AssistantSkillUpdateDTO,
)
from .assistant_skill_file_store import AssistantSkillFileStore
from .assistant_skill_support import build_runtime_skill
from ..factory_support import build_default_assistant_skill_store


class AssistantSkillService:
    def __init__(
        self,
        *,
        config_loader: ConfigLoader,
        project_service: ProjectService,
        skill_store: AssistantSkillFileStore | None = None,
    ) -> None:
        self.config_loader = config_loader
        self.project_service = project_service
        self.skill_store = skill_store or build_default_assistant_skill_store()

    async def list_user_skills(
        self,
        db: AsyncSession,
        *,
        owner_id: uuid.UUID,
    ) -> list[AssistantSkillSummaryDTO]:
        del db
        return self.skill_store.list_user_skills(owner_id)

    async def get_user_skill(
        self,
        db: AsyncSession,
        skill_id: str,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantSkillDetailDTO:
        del db
        return self.skill_store.load_user_skill(owner_id, skill_id)

    async def list_project_skills(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> list[AssistantSkillSummaryDTO]:
        return self.skill_store.list_project_skills(
            await self._require_project_id(db, project_id, owner_id=owner_id)
        )

    async def get_project_skill(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        skill_id: str,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantSkillDetailDTO:
        return self.skill_store.load_project_skill(
            await self._require_project_id(db, project_id, owner_id=owner_id),
            skill_id,
        )

    async def create_user_skill(
        self,
        db: AsyncSession,
        payload: AssistantSkillCreateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantSkillDetailDTO:
        del db
        return self.skill_store.create_user_skill(
            owner_id,
            payload,
            reserved_ids=self._reserved_skill_ids(),
        )

    async def create_project_skill(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        payload: AssistantSkillCreateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantSkillDetailDTO:
        return self.skill_store.create_project_skill(
            await self._require_project_id(db, project_id, owner_id=owner_id),
            payload,
            reserved_ids=self._reserved_skill_ids(),
        )

    async def update_user_skill(
        self,
        db: AsyncSession,
        skill_id: str,
        payload: AssistantSkillUpdateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantSkillDetailDTO:
        del db
        return self.skill_store.update_user_skill(owner_id, skill_id, payload)

    async def update_project_skill(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        skill_id: str,
        payload: AssistantSkillUpdateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantSkillDetailDTO:
        return self.skill_store.update_project_skill(
            await self._require_project_id(db, project_id, owner_id=owner_id),
            skill_id,
            payload,
        )

    async def delete_user_skill(
        self,
        db: AsyncSession,
        skill_id: str,
        *,
        owner_id: uuid.UUID,
    ) -> None:
        del db
        self.skill_store.delete_user_skill(owner_id, skill_id)

    async def delete_project_skill(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        skill_id: str,
        *,
        owner_id: uuid.UUID,
    ) -> None:
        self.skill_store.delete_project_skill(
            await self._require_project_id(db, project_id, owner_id=owner_id),
            skill_id,
        )

    def resolve_skill(
        self,
        skill_id: str,
        *,
        owner_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        allow_disabled: bool = False,
    ):
        if project_id is not None:
            project_skill = self.skill_store.find_project_skill(project_id, skill_id)
            if project_skill is not None:
                return self._resolve_custom_skill(project_skill, allow_disabled=allow_disabled)
        user_skill = self.skill_store.find_user_skill(owner_id, skill_id)
        if user_skill is not None:
            return self._resolve_custom_skill(user_skill, allow_disabled=allow_disabled)
        return self.config_loader.load_skill(skill_id)

    def _reserved_skill_ids(self) -> set[str]:
        return {skill.id for skill in self.config_loader.list_skills()}

    def _resolve_custom_skill(self, skill, *, allow_disabled: bool):
        if not allow_disabled and not skill.enabled:
            raise BusinessRuleError("这个 Skill 已停用，请先启用后再使用。")
        return build_runtime_skill(skill)

    async def _require_project_id(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> uuid.UUID:
        return (await self.project_service.require_project(db, project_id, owner_id=owner_id)).id
