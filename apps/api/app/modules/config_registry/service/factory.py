from __future__ import annotations

from pathlib import Path

from app.modules.config_registry import ConfigLoader

from .agent_write_service import ConfigRegistryAgentWriteService
from .hook_write_service import ConfigRegistryHookWriteService
from .mcp_write_service import ConfigRegistryMcpWriteService
from .query_service import ConfigRegistryQueryService
from .skill_write_service import ConfigRegistrySkillWriteService
from .workflow_write_service import ConfigRegistryWorkflowWriteService

DEFAULT_CONFIG_ROOT = Path(__file__).resolve().parents[6] / "config"


def create_config_registry_query_service(
    *,
    config_loader: ConfigLoader | None = None,
) -> ConfigRegistryQueryService:
    return ConfigRegistryQueryService(config_loader or ConfigLoader(DEFAULT_CONFIG_ROOT))


def create_config_registry_agent_write_service(
    *,
    config_loader: ConfigLoader | None = None,
) -> ConfigRegistryAgentWriteService:
    return ConfigRegistryAgentWriteService(config_loader or ConfigLoader(DEFAULT_CONFIG_ROOT))


def create_config_registry_hook_write_service(
    *,
    config_loader: ConfigLoader | None = None,
) -> ConfigRegistryHookWriteService:
    return ConfigRegistryHookWriteService(config_loader or ConfigLoader(DEFAULT_CONFIG_ROOT))


def create_config_registry_mcp_write_service(
    *,
    config_loader: ConfigLoader | None = None,
) -> ConfigRegistryMcpWriteService:
    return ConfigRegistryMcpWriteService(config_loader or ConfigLoader(DEFAULT_CONFIG_ROOT))


def create_config_registry_skill_write_service(
    *,
    config_loader: ConfigLoader | None = None,
) -> ConfigRegistrySkillWriteService:
    return ConfigRegistrySkillWriteService(config_loader or ConfigLoader(DEFAULT_CONFIG_ROOT))


def create_config_registry_workflow_write_service(
    *,
    config_loader: ConfigLoader | None = None,
) -> ConfigRegistryWorkflowWriteService:
    return ConfigRegistryWorkflowWriteService(config_loader or ConfigLoader(DEFAULT_CONFIG_ROOT))
