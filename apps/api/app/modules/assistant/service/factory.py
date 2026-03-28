from __future__ import annotations

from pathlib import Path

from app.modules.config_registry import ConfigLoader
from app.modules.credential.service import create_credential_service
from app.modules.project.service import create_project_service
from app.shared.runtime import LLMToolProvider, SkillTemplateRenderer

from .assistant_config_file_store import AssistantConfigFileStore
from .assistant_rule_service import AssistantRuleService
from .assistant_service import AssistantService
from .factory_support import build_default_assistant_config_store
from .preferences_service import AssistantPreferencesService

DEFAULT_CONFIG_ROOT = Path(__file__).resolve().parents[6] / "config"


def create_assistant_service(
    *,
    config_loader: ConfigLoader | None = None,
    config_store: AssistantConfigFileStore | None = None,
    tool_provider: LLMToolProvider | None = None,
) -> AssistantService:
    resolved_config_store = config_store or build_default_assistant_config_store()
    return AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=resolved_config_store),
        assistant_preferences_service=create_assistant_preferences_service(
            config_store=resolved_config_store
        ),
        config_loader=config_loader or ConfigLoader(DEFAULT_CONFIG_ROOT),
        credential_service_factory=create_credential_service,
        project_service=create_project_service(),
        tool_provider=tool_provider or LLMToolProvider(),
        template_renderer=SkillTemplateRenderer(),
    )


def create_assistant_rule_service(
    *,
    config_store: AssistantConfigFileStore | None = None,
) -> AssistantRuleService:
    return AssistantRuleService(
        project_service=create_project_service(),
        config_store=config_store,
    )


def create_assistant_preferences_service(
    *,
    config_store: AssistantConfigFileStore | None = None,
) -> AssistantPreferencesService:
    return AssistantPreferencesService(config_store=config_store)
