from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.project.service import ProjectService

from .assistant_config_file_store import AssistantConfigFileStore
from .preferences_dto import AssistantPreferencesDTO, AssistantPreferencesUpdateDTO
from .factory_support import build_default_assistant_config_store


class AssistantPreferencesService:
    def __init__(
        self,
        project_service: ProjectService,
        *,
        config_store: AssistantConfigFileStore | None = None,
    ) -> None:
        self.project_service = project_service
        self.config_store = config_store or build_default_assistant_config_store()

    async def get_user_preferences(
        self,
        db: AsyncSession,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantPreferencesDTO:
        del db
        return self.config_store.load_user_preferences(owner_id)

    async def update_user_preferences(
        self,
        db: AsyncSession,
        *,
        owner_id: uuid.UUID,
        payload: AssistantPreferencesUpdateDTO,
    ) -> AssistantPreferencesDTO:
        del db
        return self.config_store.save_user_preferences(owner_id, payload)

    async def get_project_preferences(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantPreferencesDTO:
        project = await self.project_service.require_project(db, project_id, owner_id=owner_id)
        return self.config_store.load_project_preferences(project.id)

    async def update_project_preferences(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        payload: AssistantPreferencesUpdateDTO,
    ) -> AssistantPreferencesDTO:
        project = await self.project_service.require_project(db, project_id, owner_id=owner_id)
        return self.config_store.save_project_preferences(project.id, payload)

    async def resolve_preferences(
        self,
        db: AsyncSession,
        *,
        owner_id: uuid.UUID,
        project_id: uuid.UUID | None,
    ) -> AssistantPreferencesDTO:
        if project_id is None:
            return await self.get_user_preferences(db, owner_id=owner_id)
        project = await self.project_service.require_project(db, project_id, owner_id=owner_id)
        return self.config_store.resolve_preferences(user_id=owner_id, project_id=project.id)

    async def get_preferences(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> AssistantPreferencesDTO:
        return await self.get_user_preferences(db, owner_id=user_id)

    async def update_preferences(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        payload: AssistantPreferencesUpdateDTO,
    ) -> AssistantPreferencesDTO:
        return await self.update_user_preferences(db, owner_id=user_id, payload=payload)
