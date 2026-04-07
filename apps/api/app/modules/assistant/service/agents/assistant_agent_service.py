from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry import ConfigLoader
from app.shared.runtime.errors import BusinessRuleError

from .assistant_agent_dto import (
    AssistantAgentCreateDTO,
    AssistantAgentDetailDTO,
    AssistantAgentSummaryDTO,
    AssistantAgentUpdateDTO,
)
from .assistant_agent_file_store import AssistantAgentFileStore
from .assistant_agent_support import build_runtime_agent, detail_to_record
from ..factory_support import build_default_assistant_agent_store
from ..skills.assistant_skill_service import AssistantSkillService


class AssistantAgentService:
    def __init__(
        self,
        *,
        config_loader: ConfigLoader,
        assistant_skill_service: AssistantSkillService,
        agent_store: AssistantAgentFileStore | None = None,
    ) -> None:
        self.config_loader = config_loader
        self.assistant_skill_service = assistant_skill_service
        self.agent_store = agent_store or build_default_assistant_agent_store()

    async def list_user_agents(
        self,
        db: AsyncSession,
        *,
        owner_id: uuid.UUID,
    ) -> list[AssistantAgentSummaryDTO]:
        del db
        return self.agent_store.list_user_agents(owner_id)

    async def get_user_agent(
        self,
        db: AsyncSession,
        agent_id: str,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantAgentDetailDTO:
        del db
        return self.agent_store.load_user_agent(owner_id, agent_id)

    async def create_user_agent(
        self,
        db: AsyncSession,
        payload: AssistantAgentCreateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantAgentDetailDTO:
        del db
        return self.agent_store.create_user_agent(
            owner_id,
            payload,
            reserved_ids=self._reserved_agent_ids(),
            validate_detail=lambda detail: self._validate_detail(detail, owner_id=owner_id),
        )

    async def update_user_agent(
        self,
        db: AsyncSession,
        agent_id: str,
        payload: AssistantAgentUpdateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantAgentDetailDTO:
        del db
        return self.agent_store.update_user_agent(
            owner_id,
            agent_id,
            payload,
            validate_detail=lambda detail: self._validate_detail(detail, owner_id=owner_id),
        )

    async def delete_user_agent(
        self,
        db: AsyncSession,
        agent_id: str,
        *,
        owner_id: uuid.UUID,
    ) -> None:
        del db
        self.agent_store.delete_user_agent(owner_id, agent_id)

    def resolve_agent(self, agent_id: str, *, owner_id: uuid.UUID, allow_disabled: bool = False):
        user_agent = self.agent_store.find_user_agent(owner_id, agent_id)
        if user_agent is not None:
            if not allow_disabled and not user_agent.enabled:
                raise BusinessRuleError("这个 Agent 已停用，请先启用后再使用。")
            self.assistant_skill_service.resolve_skill(
                user_agent.skill_id,
                owner_id=owner_id,
                allow_disabled=True,
            )
            return build_runtime_agent(user_agent)
        return self.config_loader.load_agent(agent_id)

    def _validate_detail(self, detail: AssistantAgentDetailDTO, *, owner_id: uuid.UUID) -> None:
        self.assistant_skill_service.resolve_skill(
            detail.skill_id,
            owner_id=owner_id,
            allow_disabled=True,
        )
        build_runtime_agent(detail_to_record(detail, path=self.agent_store.root))

    def _reserved_agent_ids(self) -> set[str]:
        return {agent.id for agent in self.config_loader.list_agents()}
