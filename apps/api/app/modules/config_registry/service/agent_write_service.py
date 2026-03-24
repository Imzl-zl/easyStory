from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.infrastructure.config_writer import (
    YAML_ROOT_KEY_AGENT,
    clone_config_root,
    write_config_document,
)
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError

from .agent_write_support import (
    build_agent_config,
    ensure_matching_agent_id,
    require_agent,
    serialize_agent_document,
)
from .query_dto import AgentConfigDetailDTO, AgentConfigUpdateDTO
from .query_support import to_agent_detail


class ConfigRegistryAgentWriteService:
    def __init__(self, config_loader: ConfigLoader) -> None:
        self.config_loader = config_loader

    async def update_agent(
        self,
        agent_id: str,
        payload: AgentConfigUpdateDTO,
    ) -> AgentConfigDetailDTO:
        require_agent(self.config_loader, agent_id)
        ensure_matching_agent_id(agent_id, payload.id)
        updated_agent = build_agent_config(payload)
        target_path = self.config_loader.get_source_path(agent_id)
        relative_path = target_path.relative_to(self.config_loader.config_root)
        document = serialize_agent_document(updated_agent)
        self._validate_staged_update(relative_path, document)
        write_config_document(target_path, root_key=YAML_ROOT_KEY_AGENT, payload=document)
        self.config_loader.reload()
        return to_agent_detail(require_agent(self.config_loader, agent_id))

    def _validate_staged_update(
        self,
        relative_path: Path,
        document: dict,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            staged_root = clone_config_root(self.config_loader.config_root, Path(temp_dir))
            staged_path = staged_root / relative_path
            write_config_document(staged_path, root_key=YAML_ROOT_KEY_AGENT, payload=document)
            try:
                ConfigLoader(staged_root)
            except ConfigurationError as exc:
                raise BusinessRuleError(str(exc)) from exc
