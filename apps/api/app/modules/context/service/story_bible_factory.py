from __future__ import annotations

from app.modules.project.service import ProjectService, create_project_service

from .story_bible_service import StoryBibleService


def create_story_bible_service(
    *,
    project_service: ProjectService | None = None,
) -> StoryBibleService:
    return StoryBibleService(project_service or create_project_service())
