from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from .assistant_config_file_store import AssistantConfigFileStore
from .preferences_dto import AssistantPreferencesDTO, AssistantPreferencesUpdateDTO
from .factory_support import build_default_assistant_config_store


class AssistantPreferencesService:
    def __init__(self, config_store: AssistantConfigFileStore | None = None) -> None:
        self.config_store = config_store or build_default_assistant_config_store()

    async def get_preferences(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> AssistantPreferencesDTO:
        del db
        return self.config_store.load_preferences(user_id)

    async def update_preferences(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        payload: AssistantPreferencesUpdateDTO,
    ) -> AssistantPreferencesDTO:
        del db
        return self.config_store.save_preferences(user_id, payload)
