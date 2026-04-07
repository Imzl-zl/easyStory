from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry import ConfigLoader
from app.shared.runtime.errors import BusinessRuleError

from ..agents.assistant_agent_service import AssistantAgentService
from .assistant_hook_dto import (
    AssistantHookCreateDTO,
    AssistantHookDetailDTO,
    AssistantHookSummaryDTO,
    AssistantHookUpdateDTO,
)
from .assistant_hook_file_store import AssistantHookFileStore
from ..mcp.assistant_mcp_service import AssistantMcpService
from .assistant_user_hook_support import build_runtime_hook, detail_to_record
from ..factory_support import build_default_assistant_hook_store


class AssistantHookService:
    def __init__(
        self,
        *,
        assistant_agent_service: AssistantAgentService,
        assistant_mcp_service: AssistantMcpService,
        config_loader: ConfigLoader,
        hook_store: AssistantHookFileStore | None = None,
    ) -> None:
        self.assistant_agent_service = assistant_agent_service
        self.assistant_mcp_service = assistant_mcp_service
        self.config_loader = config_loader
        self.hook_store = hook_store or build_default_assistant_hook_store()

    async def list_user_hooks(
        self,
        db: AsyncSession,
        *,
        owner_id: uuid.UUID,
    ) -> list[AssistantHookSummaryDTO]:
        del db
        return self.hook_store.list_user_hooks(owner_id)

    async def get_user_hook(
        self,
        db: AsyncSession,
        hook_id: str,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantHookDetailDTO:
        del db
        return self.hook_store.load_user_hook(owner_id, hook_id)

    async def create_user_hook(
        self,
        db: AsyncSession,
        payload: AssistantHookCreateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantHookDetailDTO:
        del db
        return self.hook_store.create_user_hook(
            owner_id,
            payload,
            reserved_ids=self._reserved_hook_ids(),
            validate_detail=lambda detail: self._validate_detail(detail, owner_id=owner_id),
        )

    async def update_user_hook(
        self,
        db: AsyncSession,
        hook_id: str,
        payload: AssistantHookUpdateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantHookDetailDTO:
        del db
        return self.hook_store.update_user_hook(
            owner_id,
            hook_id,
            payload,
            validate_detail=lambda detail: self._validate_detail(detail, owner_id=owner_id),
        )

    async def delete_user_hook(
        self,
        db: AsyncSession,
        hook_id: str,
        *,
        owner_id: uuid.UUID,
    ) -> None:
        del db
        self.hook_store.delete_user_hook(owner_id, hook_id)

    def resolve_hook(self, hook_id: str, *, owner_id: uuid.UUID, allow_disabled: bool = False):
        user_hook = self.hook_store.find_user_hook(owner_id, hook_id)
        if user_hook is not None:
            if not allow_disabled and not user_hook.enabled:
                raise BusinessRuleError("这个 Hook 已停用，请先启用后再使用。")
            self._validate_action_dependency(
                user_hook.action,
                owner_id=owner_id,
                allow_disabled=False,
            )
            return build_runtime_hook(user_hook)
        return self.config_loader.load_hook(hook_id)

    def _validate_detail(self, detail: AssistantHookDetailDTO, *, owner_id: uuid.UUID) -> None:
        self._validate_action_dependency(
            detail.action,
            owner_id=owner_id,
            allow_disabled=True,
        )
        build_runtime_hook(detail_to_record(detail, path=self.hook_store.root))

    def _reserved_hook_ids(self) -> set[str]:
        return {hook.id for hook in self.config_loader.list_hooks()}

    def _validate_action_dependency(
        self,
        action,
        *,
        owner_id: uuid.UUID,
        allow_disabled: bool,
    ) -> None:
        if action.action_type == "agent":
            self.assistant_agent_service.resolve_agent(
                action.agent_id,
                owner_id=owner_id,
                allow_disabled=True,
            )
            return
        self.assistant_mcp_service.resolve_mcp_server(
            action.server_id,
            owner_id=owner_id,
            allow_disabled=allow_disabled,
        )
