from __future__ import annotations

from app.modules.project.service import ProjectService, create_project_service

from .story_asset_service import StoryAssetService


def create_story_asset_service(
    *,
    project_service: ProjectService | None = None,
) -> StoryAssetService:
    return StoryAssetService(project_service or create_project_service())
