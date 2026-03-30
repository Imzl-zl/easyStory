from __future__ import annotations

from pathlib import Path

from app.modules.config_registry import ConfigLoader
from app.modules.credential.service import create_credential_service
from app.modules.project.service import ProjectService, create_project_service
from app.shared.runtime import LLMToolProvider, SkillTemplateRenderer

from .assistant_config_file_store import AssistantConfigFileStore
from .assistant_agent_file_store import AssistantAgentFileStore
from .assistant_agent_service import AssistantAgentService
from .assistant_hook_file_store import AssistantHookFileStore
from .assistant_hook_service import AssistantHookService
from .assistant_mcp_file_store import AssistantMcpFileStore
from .assistant_mcp_service import AssistantMcpService
from .assistant_skill_file_store import AssistantSkillFileStore
from .assistant_rule_service import AssistantRuleService
from .assistant_skill_service import AssistantSkillService
from .assistant_service import AssistantService
from .factory_support import (
    build_default_assistant_agent_store,
    build_default_assistant_config_store,
    build_default_assistant_hook_store,
    build_default_assistant_mcp_store,
    build_default_assistant_skill_store,
)
from .preferences_service import AssistantPreferencesService

DEFAULT_CONFIG_ROOT = Path(__file__).resolve().parents[6] / "config"


def create_assistant_service(
    *,
    config_loader: ConfigLoader | None = None,
    config_store: AssistantConfigFileStore | None = None,
    agent_store: AssistantAgentFileStore | None = None,
    hook_store: AssistantHookFileStore | None = None,
    mcp_store: AssistantMcpFileStore | None = None,
    skill_store: AssistantSkillFileStore | None = None,
    tool_provider: LLMToolProvider | None = None,
) -> AssistantService:
    resolved_config_store = config_store or build_default_assistant_config_store()
    resolved_config_loader = config_loader or ConfigLoader(DEFAULT_CONFIG_ROOT)
    resolved_project_service = create_project_service()
    resolved_skill_store = skill_store or build_default_assistant_skill_store()
    resolved_skill_service = create_assistant_skill_service(
        config_loader=resolved_config_loader,
        project_service=resolved_project_service,
        skill_store=resolved_skill_store,
    )
    resolved_agent_service = create_assistant_agent_service(
        assistant_skill_service=resolved_skill_service,
        agent_store=agent_store,
        config_loader=resolved_config_loader,
    )
    resolved_mcp_service = create_assistant_mcp_service(
        config_loader=resolved_config_loader,
        project_service=resolved_project_service,
        mcp_store=mcp_store,
    )
    return AssistantService(
        assistant_agent_service=resolved_agent_service,
        assistant_hook_service=create_assistant_hook_service(
            assistant_agent_service=resolved_agent_service,
            assistant_mcp_service=resolved_mcp_service,
            config_loader=resolved_config_loader,
            hook_store=hook_store,
        ),
        assistant_mcp_service=resolved_mcp_service,
        assistant_rule_service=create_assistant_rule_service(
            config_store=resolved_config_store,
            project_service=resolved_project_service,
        ),
        assistant_preferences_service=create_assistant_preferences_service(
            config_store=resolved_config_store,
            project_service=resolved_project_service,
        ),
        assistant_skill_service=resolved_skill_service,
        config_loader=resolved_config_loader,
        credential_service_factory=create_credential_service,
        project_service=resolved_project_service,
        tool_provider=tool_provider or LLMToolProvider(),
        template_renderer=SkillTemplateRenderer(),
    )


def create_assistant_rule_service(
    *,
    config_store: AssistantConfigFileStore | None = None,
    project_service: ProjectService | None = None,
) -> AssistantRuleService:
    return AssistantRuleService(
        project_service=project_service or create_project_service(),
        config_store=config_store,
    )


def create_assistant_preferences_service(
    *,
    config_store: AssistantConfigFileStore | None = None,
    project_service: ProjectService | None = None,
) -> AssistantPreferencesService:
    return AssistantPreferencesService(
        project_service=project_service or create_project_service(),
        config_store=config_store,
    )


def create_assistant_skill_service(
    *,
    config_loader: ConfigLoader | None = None,
    project_service: ProjectService | None = None,
    skill_store: AssistantSkillFileStore | None = None,
) -> AssistantSkillService:
    return AssistantSkillService(
        config_loader=config_loader or ConfigLoader(DEFAULT_CONFIG_ROOT),
        project_service=project_service or create_project_service(),
        skill_store=skill_store,
    )


def create_assistant_agent_service(
    *,
    assistant_skill_service: AssistantSkillService | None = None,
    agent_store: AssistantAgentFileStore | None = None,
    config_loader: ConfigLoader | None = None,
) -> AssistantAgentService:
    resolved_config_loader = config_loader or ConfigLoader(DEFAULT_CONFIG_ROOT)
    resolved_skill_service = assistant_skill_service or create_assistant_skill_service(
        config_loader=resolved_config_loader,
    )
    return AssistantAgentService(
        assistant_skill_service=resolved_skill_service,
        agent_store=agent_store or build_default_assistant_agent_store(),
        config_loader=resolved_config_loader,
    )


def create_assistant_hook_service(
    *,
    assistant_agent_service: AssistantAgentService | None = None,
    assistant_mcp_service: AssistantMcpService | None = None,
    config_loader: ConfigLoader | None = None,
    hook_store: AssistantHookFileStore | None = None,
) -> AssistantHookService:
    resolved_config_loader = config_loader or ConfigLoader(DEFAULT_CONFIG_ROOT)
    resolved_agent_service = assistant_agent_service or create_assistant_agent_service(
        config_loader=resolved_config_loader,
    )
    resolved_mcp_service = assistant_mcp_service or create_assistant_mcp_service(
        config_loader=resolved_config_loader,
    )
    return AssistantHookService(
        assistant_agent_service=resolved_agent_service,
        assistant_mcp_service=resolved_mcp_service,
        config_loader=resolved_config_loader,
        hook_store=hook_store or build_default_assistant_hook_store(),
    )


def create_assistant_mcp_service(
    *,
    config_loader: ConfigLoader | None = None,
    project_service: ProjectService | None = None,
    mcp_store: AssistantMcpFileStore | None = None,
) -> AssistantMcpService:
    return AssistantMcpService(
        config_loader=config_loader or ConfigLoader(DEFAULT_CONFIG_ROOT),
        project_service=project_service or create_project_service(),
        mcp_store=mcp_store or build_default_assistant_mcp_store(),
    )
