from __future__ import annotations

from app.shared.settings import get_settings

from .assistant_config_file_store import AssistantConfigFileStore
from .assistant_agent_file_store import AssistantAgentFileStore
from .assistant_hook_file_store import AssistantHookFileStore
from .assistant_mcp_file_store import AssistantMcpFileStore
from .assistant_skill_file_store import AssistantSkillFileStore


def build_default_assistant_config_store() -> AssistantConfigFileStore:
    return AssistantConfigFileStore(get_settings().assistant_config_root)


def build_default_assistant_skill_store() -> AssistantSkillFileStore:
    return AssistantSkillFileStore(get_settings().assistant_config_root)


def build_default_assistant_agent_store() -> AssistantAgentFileStore:
    return AssistantAgentFileStore(get_settings().assistant_config_root)


def build_default_assistant_hook_store() -> AssistantHookFileStore:
    return AssistantHookFileStore(get_settings().assistant_config_root)


def build_default_assistant_mcp_store() -> AssistantMcpFileStore:
    return AssistantMcpFileStore(get_settings().assistant_config_root)
