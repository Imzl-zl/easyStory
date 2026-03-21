from __future__ import annotations

from app.modules.context.engine import ContextBuilder, create_context_builder
from app.shared.runtime import SkillTemplateRenderer

from .context_preview_service import ContextPreviewService


def create_context_preview_service(
    *,
    context_builder: ContextBuilder | None = None,
    template_renderer: SkillTemplateRenderer | None = None,
) -> ContextPreviewService:
    return ContextPreviewService(
        context_builder=context_builder or create_context_builder(),
        template_renderer=template_renderer or SkillTemplateRenderer(),
    )
