from __future__ import annotations

from collections.abc import Callable

from app.modules.context.engine import ContextBuilder, create_context_builder
from app.modules.credential.service import (
    CredentialService,
    create_credential_resolution_service,
)
from app.shared.runtime import SkillTemplateRenderer

from .context_preview_service import ContextPreviewService


def create_context_preview_service(
    *,
    context_builder: ContextBuilder | None = None,
    template_renderer: SkillTemplateRenderer | None = None,
    credential_service_factory: Callable[[], CredentialService] | None = None,
) -> ContextPreviewService:
    return ContextPreviewService(
        context_builder=context_builder or create_context_builder(),
        template_renderer=template_renderer or SkillTemplateRenderer(),
        credential_service_factory=credential_service_factory or create_credential_resolution_service,
    )
