from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.infrastructure.config_writer import (
    YAML_ROOT_KEY_MCP_SERVER,
    clone_config_root,
    write_config_document,
)
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError

from .mcp_query_dto import McpServerConfigDetailDTO, McpServerConfigUpdateDTO
from .mcp_write_support import (
    build_mcp_server_config,
    ensure_matching_mcp_server_id,
    require_mcp_server,
    serialize_mcp_server_document,
)
from .query_support import to_mcp_server_detail


class ConfigRegistryMcpWriteService:
    def __init__(self, config_loader: ConfigLoader) -> None:
        self.config_loader = config_loader

    async def update_mcp_server(
        self,
        server_id: str,
        payload: McpServerConfigUpdateDTO,
    ) -> McpServerConfigDetailDTO:
        require_mcp_server(self.config_loader, server_id)
        ensure_matching_mcp_server_id(server_id, payload.id)
        updated_server = build_mcp_server_config(payload)
        target_path = self.config_loader.get_source_path(server_id)
        relative_path = target_path.relative_to(self.config_loader.config_root)
        document = serialize_mcp_server_document(updated_server)
        self._validate_staged_update(relative_path, document)
        write_config_document(target_path, root_key=YAML_ROOT_KEY_MCP_SERVER, payload=document)
        self.config_loader.reload()
        return to_mcp_server_detail(require_mcp_server(self.config_loader, server_id))

    def _validate_staged_update(
        self,
        relative_path: Path,
        document: dict[str, object],
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            staged_root = clone_config_root(self.config_loader.config_root, Path(temp_dir))
            staged_path = staged_root / relative_path
            write_config_document(staged_path, root_key=YAML_ROOT_KEY_MCP_SERVER, payload=document)
            try:
                ConfigLoader(staged_root)
            except ConfigurationError as exc:
                raise BusinessRuleError(str(exc)) from exc
