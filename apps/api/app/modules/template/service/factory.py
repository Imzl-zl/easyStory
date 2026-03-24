from __future__ import annotations

from pathlib import Path

from app.modules.config_registry import ConfigLoader

from .builtin_template_sync_service import BuiltinTemplateSyncService
from .template_query_service import TemplateQueryService
from .template_write_service import TemplateWriteService

DEFAULT_CONFIG_ROOT = Path(__file__).resolve().parents[6] / "config"


def create_builtin_template_sync_service(
    *,
    config_loader: ConfigLoader | None = None,
) -> BuiltinTemplateSyncService:
    return BuiltinTemplateSyncService(config_loader or ConfigLoader(DEFAULT_CONFIG_ROOT))


def create_template_query_service() -> TemplateQueryService:
    return TemplateQueryService()


def create_template_write_service(
    *,
    config_loader: ConfigLoader | None = None,
    query_service: TemplateQueryService | None = None,
) -> TemplateWriteService:
    return TemplateWriteService(
        config_loader or ConfigLoader(DEFAULT_CONFIG_ROOT),
        query_service=query_service,
    )
