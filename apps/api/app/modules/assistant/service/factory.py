from __future__ import annotations

from pathlib import Path

from app.modules.config_registry import ConfigLoader
from app.modules.credential.service import create_credential_service
from app.modules.project.service import (
    ProjectDocumentCapabilityService,
    ProjectService,
    create_project_document_capability_service,
    create_project_service,
)
from app.shared.runtime import LLMToolProvider, SkillTemplateRenderer

from .assistant_config_file_store import AssistantConfigFileStore
from .assistant_agent_file_store import AssistantAgentFileStore
from .assistant_agent_service import AssistantAgentService
from .assistant_hook_file_store import AssistantHookFileStore
from .assistant_hook_service import AssistantHookService
from .assistant_mcp_file_store import AssistantMcpFileStore
from .assistant_mcp_service import AssistantMcpService
from .assistant_tool_executor import AssistantToolExecutor
from .assistant_tool_exposure_policy import AssistantToolExposurePolicy
from .assistant_tool_loop import AssistantToolLoop
from .assistant_tool_registry import AssistantToolDescriptorRegistry
from .assistant_tool_step_store import AssistantToolStepStore
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
    build_default_assistant_tool_step_store,
    build_default_assistant_turn_run_store,
)
from .preferences_service import AssistantPreferencesService
from .assistant_turn_run_store import AssistantTurnRunStore

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
    tool_step_store: AssistantToolStepStore | None = None,
    turn_run_store: AssistantTurnRunStore | None = None,
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
    resolved_tool_registry = create_assistant_tool_descriptor_registry()
    resolved_tool_exposure_policy = create_assistant_tool_exposure_policy(
        registry=resolved_tool_registry,
    )
    resolved_project_document_capability_service = create_project_document_capability_service(
        project_service=resolved_project_service,
    )
    resolved_tool_executor = create_assistant_tool_executor(
        project_document_capability_service=resolved_project_document_capability_service,
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
        assistant_tool_descriptor_registry=resolved_tool_registry,
        assistant_tool_exposure_policy=resolved_tool_exposure_policy,
        assistant_tool_executor=resolved_tool_executor,
        assistant_tool_loop=create_assistant_tool_loop(
            exposure_policy=resolved_tool_exposure_policy,
            executor=resolved_tool_executor,
            step_store=tool_step_store or build_default_assistant_tool_step_store(),
        ),
        turn_run_store=turn_run_store or build_default_assistant_turn_run_store(),
        project_document_capability_service=resolved_project_document_capability_service,
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


def create_assistant_tool_descriptor_registry() -> AssistantToolDescriptorRegistry:
    return AssistantToolDescriptorRegistry()


def create_assistant_tool_exposure_policy(
    *,
    registry: AssistantToolDescriptorRegistry | None = None,
) -> AssistantToolExposurePolicy:
    return AssistantToolExposurePolicy(
        registry=registry or create_assistant_tool_descriptor_registry(),
    )


def create_assistant_tool_executor(
    *,
    project_document_capability_service: ProjectDocumentCapabilityService | None = None,
) -> AssistantToolExecutor:
    return AssistantToolExecutor(
        project_document_capability_service=project_document_capability_service
        or create_project_document_capability_service(),
    )


def create_assistant_tool_loop(
    *,
    exposure_policy: AssistantToolExposurePolicy | None = None,
    executor: AssistantToolExecutor | None = None,
    step_store: AssistantToolStepStore | None = None,
) -> AssistantToolLoop:
    resolved_exposure_policy = exposure_policy or create_assistant_tool_exposure_policy()
    resolved_executor = executor or create_assistant_tool_executor()
    return AssistantToolLoop(
        exposure_policy=resolved_exposure_policy,
        executor=resolved_executor,
        step_store=step_store,
    )


def create_assistant_tool_step_store() -> AssistantToolStepStore:
    return build_default_assistant_tool_step_store()
