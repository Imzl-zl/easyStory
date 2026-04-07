from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry import ConfigLoader
from app.modules.project.service import ProjectService
from app.shared.runtime.errors import BusinessRuleError

from .assistant_mcp_dto import (
    AssistantMcpCreateDTO,
    AssistantMcpDetailDTO,
    AssistantMcpSummaryDTO,
    AssistantMcpUpdateDTO,
)
from .assistant_mcp_file_store import AssistantMcpFileStore
from .assistant_user_mcp_support import build_runtime_mcp
from ..factory_support import build_default_assistant_mcp_store


class AssistantMcpService:
    def __init__(
        self,
        *,
        config_loader: ConfigLoader,
        project_service: ProjectService,
        mcp_store: AssistantMcpFileStore | None = None,
    ) -> None:
        self.config_loader = config_loader
        self.project_service = project_service
        self.mcp_store = mcp_store or build_default_assistant_mcp_store()

    async def list_user_mcp_servers(
        self,
        db: AsyncSession,
        *,
        owner_id: uuid.UUID,
    ) -> list[AssistantMcpSummaryDTO]:
        del db
        return self.mcp_store.list_user_mcp_servers(owner_id)

    async def get_user_mcp_server(
        self,
        db: AsyncSession,
        server_id: str,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantMcpDetailDTO:
        del db
        return self.mcp_store.load_user_mcp_server(owner_id, server_id)

    async def list_project_mcp_servers(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> list[AssistantMcpSummaryDTO]:
        return self.mcp_store.list_project_mcp_servers(
            await self._require_project_id(db, project_id, owner_id=owner_id)
        )

    async def get_project_mcp_server(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        server_id: str,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantMcpDetailDTO:
        return self.mcp_store.load_project_mcp_server(
            await self._require_project_id(db, project_id, owner_id=owner_id),
            server_id,
        )

    async def create_user_mcp_server(
        self,
        db: AsyncSession,
        payload: AssistantMcpCreateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantMcpDetailDTO:
        del db
        return self.mcp_store.create_user_mcp_server(
            owner_id,
            payload,
            reserved_ids=self._reserved_mcp_ids(),
        )

    async def create_project_mcp_server(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        payload: AssistantMcpCreateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantMcpDetailDTO:
        return self.mcp_store.create_project_mcp_server(
            await self._require_project_id(db, project_id, owner_id=owner_id),
            payload,
            reserved_ids=self._reserved_mcp_ids(),
        )

    async def update_user_mcp_server(
        self,
        db: AsyncSession,
        server_id: str,
        payload: AssistantMcpUpdateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantMcpDetailDTO:
        del db
        return self.mcp_store.update_user_mcp_server(owner_id, server_id, payload)

    async def update_project_mcp_server(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        server_id: str,
        payload: AssistantMcpUpdateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> AssistantMcpDetailDTO:
        return self.mcp_store.update_project_mcp_server(
            await self._require_project_id(db, project_id, owner_id=owner_id),
            server_id,
            payload,
        )

    async def delete_user_mcp_server(
        self,
        db: AsyncSession,
        server_id: str,
        *,
        owner_id: uuid.UUID,
    ) -> None:
        del db
        self.mcp_store.delete_user_mcp_server(owner_id, server_id)

    async def delete_project_mcp_server(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        server_id: str,
        *,
        owner_id: uuid.UUID,
    ) -> None:
        self.mcp_store.delete_project_mcp_server(
            await self._require_project_id(db, project_id, owner_id=owner_id),
            server_id,
        )

    def resolve_mcp_server(
        self,
        server_id: str,
        *,
        owner_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        allow_disabled: bool = False,
    ):
        if project_id is not None:
            project_server = self.mcp_store.find_project_mcp_server(project_id, server_id)
            if project_server is not None:
                return self._resolve_custom_mcp(project_server, allow_disabled=allow_disabled)
        user_server = self.mcp_store.find_user_mcp_server(owner_id, server_id)
        if user_server is not None:
            return self._resolve_custom_mcp(user_server, allow_disabled=allow_disabled)
        return self.config_loader.load_mcp_server(server_id)

    def _reserved_mcp_ids(self) -> set[str]:
        return {server.id for server in self.config_loader.list_mcp_servers()}

    def _resolve_custom_mcp(self, server, *, allow_disabled: bool):
        if not allow_disabled and not server.enabled:
            raise BusinessRuleError("这个 MCP 已停用，请先启用后再使用。")
        return build_runtime_mcp(server)

    async def _require_project_id(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> uuid.UUID:
        return (await self.project_service.require_project(db, project_id, owner_id=owner_id)).id
