from __future__ import annotations

from app.shared.settings import get_settings

from .assistant_config_file_store import AssistantConfigFileStore
from .agents.assistant_agent_file_store import AssistantAgentFileStore
from .hooks.assistant_hook_file_store import AssistantHookFileStore
from .mcp.assistant_mcp_file_store import AssistantMcpFileStore
from .skills.assistant_skill_file_store import AssistantSkillFileStore
from .tooling.assistant_tool_step_store import AssistantToolStepStore
from .turn.assistant_turn_run_store import AssistantTurnRunStore


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


def build_default_assistant_turn_run_store() -> AssistantTurnRunStore:
    return AssistantTurnRunStore(get_settings().assistant_config_root / "turn-runs")


def build_default_assistant_tool_step_store() -> AssistantToolStepStore:
    return AssistantToolStepStore(get_settings().assistant_config_root / "tool-steps")
