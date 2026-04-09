from __future__ import annotations

from collections.abc import Callable
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.credential.service import CredentialService, create_credential_resolution_service
from app.modules.project.service import ProjectService

from ..assistant_config_file_store import AssistantConfigFileStore
from .preferences_dto import AssistantPreferencesDTO, AssistantPreferencesUpdateDTO
from .preferences_support import (
    build_updated_preferences,
    merge_preferences,
    validate_preferences_provider_native_reasoning,
)
from ..factory_support import build_default_assistant_config_store


class AssistantPreferencesService:
    def __init__(
        self,
        project_service: ProjectService,
        *,
        config_store: AssistantConfigFileStore | None = None,
        credential_service_factory: Callable[[], CredentialService] | None = None,
    ) -> None:
        self.project_service = project_service
        self.config_store = config_store or build_default_assistant_config_store()
        self.credential_service_factory = credential_service_factory or (
            lambda: create_credential_resolution_service(project_service=self.project_service)
        )

    async def get_user_preferences(
        self,
        db: AsyncSession,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantPreferencesDTO:
        stored_preferences = self.config_store.load_user_preferences(owner_id)
        return await self._normalize_preferences_for_read(
            db,
            owner_id=owner_id,
            project_id=None,
            preferences=stored_preferences,
        )

    async def update_user_preferences(
        self,
        db: AsyncSession,
        *,
        owner_id: uuid.UUID,
        payload: AssistantPreferencesUpdateDTO,
    ) -> AssistantPreferencesDTO:
        preferences = build_updated_preferences(payload)
        await self._validate_preferences_provider_native_reasoning(
            db,
            owner_id=owner_id,
            project_id=None,
            preferences=preferences,
        )
        return self.config_store.save_user_preferences(owner_id, payload)

    async def get_project_preferences(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantPreferencesDTO:
        project = await self.project_service.require_project(db, project_id, owner_id=owner_id)
        stored_preferences = self.config_store.load_project_preferences(project.id)
        return await self._normalize_preferences_for_read(
            db,
            owner_id=owner_id,
            project_id=project.id,
            preferences=stored_preferences,
        )

    async def update_project_preferences(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        payload: AssistantPreferencesUpdateDTO,
    ) -> AssistantPreferencesDTO:
        project = await self.project_service.require_project(db, project_id, owner_id=owner_id)
        project_preferences = build_updated_preferences(payload)
        effective_preferences = merge_preferences(
            self.config_store.load_user_preferences(owner_id),
            project_preferences,
        )
        await self._validate_preferences_provider_native_reasoning(
            db,
            owner_id=owner_id,
            project_id=project.id,
            preferences=effective_preferences,
        )
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
        resolved_preferences = self.config_store.resolve_preferences(
            user_id=owner_id,
            project_id=project.id,
        )
        return await self._normalize_preferences_for_read(
            db,
            owner_id=owner_id,
            project_id=project.id,
            preferences=resolved_preferences,
        )

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

    async def _validate_preferences_provider_native_reasoning(
        self,
        db: AsyncSession,
        *,
        owner_id: uuid.UUID,
        project_id: uuid.UUID | None,
        preferences: AssistantPreferencesDTO,
    ) -> None:
        del db, owner_id, project_id
        validate_preferences_provider_native_reasoning(preferences)

    async def _normalize_preferences_for_read(
        self,
        db: AsyncSession,
        *,
        owner_id: uuid.UUID,
        project_id: uuid.UUID | None,
        preferences: AssistantPreferencesDTO,
    ) -> AssistantPreferencesDTO:
        del db, owner_id, project_id
        return preferences
