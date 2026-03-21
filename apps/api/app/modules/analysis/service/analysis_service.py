from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.modules.analysis.models import Analysis
from app.modules.content.models import Content
from app.modules.project.service import ProjectService
from app.shared.runtime.errors import NotFoundError

from .dto import AnalysisCreateDTO, AnalysisDetailDTO, AnalysisSummaryDTO, AnalysisType


class AnalysisService:
    def __init__(
        self,
        project_service: ProjectService,
    ) -> None:
        self.project_service = project_service

    def create_analysis(
        self,
        db: Session,
        project_id: uuid.UUID,
        payload: AnalysisCreateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> AnalysisDetailDTO:
        self.project_service.require_project(db, project_id, owner_id=owner_id)
        if payload.content_id is not None:
            self._require_project_content(db, project_id, payload.content_id)
        analysis = Analysis(
            project_id=project_id,
            content_id=payload.content_id,
            analysis_type=payload.analysis_type,
            source_title=payload.source_title,
            analysis_scope=payload.analysis_scope,
            result=payload.result,
            suggestions=payload.suggestions,
            generated_skill_key=payload.generated_skill_key,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return self._to_detail(analysis)

    def list_analyses(
        self,
        db: Session,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        analysis_type: AnalysisType | None = None,
        content_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[AnalysisSummaryDTO]:
        self.project_service.require_project(db, project_id, owner_id=owner_id)
        if content_id is not None:
            self._require_project_content(db, project_id, content_id)
        query = db.query(Analysis).filter(Analysis.project_id == project_id)
        if analysis_type is not None:
            query = query.filter(Analysis.analysis_type == analysis_type)
        if content_id is not None:
            query = query.filter(Analysis.content_id == content_id)
        analyses = (
            query.order_by(Analysis.created_at.desc(), Analysis.id.desc())
            .limit(limit)
            .all()
        )
        return [self._to_summary(item) for item in analyses]

    def get_analysis(
        self,
        db: Session,
        project_id: uuid.UUID,
        analysis_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> AnalysisDetailDTO:
        self.project_service.require_project(db, project_id, owner_id=owner_id)
        analysis = (
            db.query(Analysis)
            .filter(
                Analysis.id == analysis_id,
                Analysis.project_id == project_id,
            )
            .one_or_none()
        )
        if analysis is None:
            raise NotFoundError(f"Analysis not found: {analysis_id}")
        return self._to_detail(analysis)

    def _require_project_content(
        self,
        db: Session,
        project_id: uuid.UUID,
        content_id: uuid.UUID,
    ) -> Content:
        content = (
            db.query(Content)
            .filter(
                Content.id == content_id,
                Content.project_id == project_id,
            )
            .one_or_none()
        )
        if content is None:
            raise NotFoundError(f"Content not found: {content_id}")
        return content

    def _to_summary(
        self,
        analysis: Analysis,
    ) -> AnalysisSummaryDTO:
        return AnalysisSummaryDTO.model_validate(analysis, from_attributes=True)

    def _to_detail(
        self,
        analysis: Analysis,
    ) -> AnalysisDetailDTO:
        return AnalysisDetailDTO.model_validate(analysis, from_attributes=True)
