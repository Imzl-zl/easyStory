from __future__ import annotations

from app.modules.project.service import (
    ProjectService,
    create_project_service,
)

from .analysis_service import AnalysisService


def create_analysis_service(
    *,
    project_service: ProjectService | None = None,
) -> AnalysisService:
    return AnalysisService(project_service or create_project_service())
