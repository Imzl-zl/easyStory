from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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

    async def create_analysis(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        payload: AnalysisCreateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> AnalysisDetailDTO:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        if payload.content_id is not None:
            await self._require_project_content(db, project_id, payload.content_id)
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
        await db.commit()
        await db.refresh(analysis)
        return self._to_detail(analysis)

    async def list_analyses(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        analysis_type: AnalysisType | None = None,
        content_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[AnalysisSummaryDTO]:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        if content_id is not None:
            await self._require_project_content(db, project_id, content_id)
        statement = select(Analysis).where(Analysis.project_id == project_id)
        if analysis_type is not None:
            statement = statement.where(Analysis.analysis_type == analysis_type)
        if content_id is not None:
            statement = statement.where(Analysis.content_id == content_id)
        statement = statement.order_by(Analysis.created_at.desc(), Analysis.id.desc()).limit(limit)
        analyses = (await db.scalars(statement)).all()
        return [self._to_summary(item) for item in analyses]

    async def get_analysis(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        analysis_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> AnalysisDetailDTO:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        analysis = await db.scalar(
            select(Analysis).where(
                Analysis.id == analysis_id,
                Analysis.project_id == project_id,
            )
        )
        if analysis is None:
            raise NotFoundError(f"Analysis not found: {analysis_id}")
        return self._to_detail(analysis)

    async def _require_project_content(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        content_id: uuid.UUID,
    ) -> Content:
        content = await db.scalar(
            select(Content).where(
                Content.id == content_id,
                Content.project_id == project_id,
            )
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
