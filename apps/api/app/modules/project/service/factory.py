from __future__ import annotations

from .project_service import ProjectService


def create_project_service() -> ProjectService:
    return ProjectService()
