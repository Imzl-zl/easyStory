from __future__ import annotations

from app.modules.context.service import StoryBibleService, create_story_bible_service
from app.modules.project.service import ProjectService, create_project_service

from .chapter_content_service import ChapterContentService
from .story_asset_service import StoryAssetService


def create_story_asset_service(
    *,
    project_service: ProjectService | None = None,
) -> StoryAssetService:
    return StoryAssetService(project_service or create_project_service())


def create_chapter_content_service(
    *,
    project_service: ProjectService | None = None,
    story_bible_service: StoryBibleService | None = None,
) -> ChapterContentService:
    return ChapterContentService(
        project_service or create_project_service(),
        story_bible_service or create_story_bible_service(),
    )
