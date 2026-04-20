from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app.modules.config_registry import ConfigLoader
from app.modules.context.service.story_bible_factory import create_story_bible_service
from app.modules.context.service.story_bible_service import StoryBibleService
from app.modules.credential.service import CredentialService, create_credential_service
from app.modules.project.service import ProjectService, create_project_service
from app.shared.runtime.llm.llm_tool_provider import LLMToolProvider
from app.shared.runtime.template_renderer import SkillTemplateRenderer
from app.shared.runtime.tool_provider import ToolProvider

from .chapter_content_service import ChapterContentService
from .canonical_project_document_query_service import CanonicalProjectDocumentQueryService
from .story_asset_generation_service import StoryAssetGenerationService
from .story_asset_service import StoryAssetService

DEFAULT_CONFIG_ROOT = Path(__file__).resolve().parents[6] / "config"


def create_story_asset_service(
    *,
    project_service: ProjectService | None = None,
) -> StoryAssetService:
    return StoryAssetService(project_service or create_project_service())


def create_story_asset_generation_service(
    *,
    project_service: ProjectService | None = None,
    story_asset_service: StoryAssetService | None = None,
    config_loader: ConfigLoader | None = None,
    credential_service_factory: Callable[[], CredentialService] | None = None,
    tool_provider: ToolProvider | None = None,
    template_renderer: SkillTemplateRenderer | None = None,
) -> StoryAssetGenerationService:
    project_service_instance = project_service or create_project_service()
    return StoryAssetGenerationService(
        project_service=project_service_instance,
        story_asset_service=story_asset_service
        or create_story_asset_service(project_service=project_service_instance),
        config_loader=config_loader or ConfigLoader(DEFAULT_CONFIG_ROOT),
        credential_service_factory=credential_service_factory
        or (
            lambda: create_credential_service(project_service=project_service_instance)
        ),
        tool_provider=tool_provider or LLMToolProvider(),
        template_renderer=template_renderer or SkillTemplateRenderer(),
    )


def create_chapter_content_service(
    *,
    project_service: ProjectService | None = None,
    story_bible_service: StoryBibleService | None = None,
) -> ChapterContentService:
    return ChapterContentService(
        project_service or create_project_service(),
        story_bible_service or create_story_bible_service(),
    )


def create_canonical_project_document_query_service(
    *,
    project_service: ProjectService | None = None,
) -> CanonicalProjectDocumentQueryService:
    return CanonicalProjectDocumentQueryService(project_service or create_project_service())
