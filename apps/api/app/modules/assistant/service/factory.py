from __future__ import annotations

from pathlib import Path

from app.modules.config_registry import ConfigLoader
from app.modules.credential.service import create_credential_service
from app.modules.project.service import create_project_service
from app.shared.runtime import LLMToolProvider, SkillTemplateRenderer

from .assistant_service import AssistantService

DEFAULT_CONFIG_ROOT = Path(__file__).resolve().parents[6] / "config"


def create_assistant_service(
    *,
    config_loader: ConfigLoader | None = None,
    tool_provider: LLMToolProvider | None = None,
) -> AssistantService:
    return AssistantService(
        config_loader=config_loader or ConfigLoader(DEFAULT_CONFIG_ROOT),
        credential_service_factory=create_credential_service,
        project_service=create_project_service(),
        tool_provider=tool_provider or LLMToolProvider(),
        template_renderer=SkillTemplateRenderer(),
    )
