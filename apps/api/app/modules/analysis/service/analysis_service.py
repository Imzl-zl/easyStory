from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analysis.models import Analysis
from app.modules.content.models import Content
from app.modules.project.service import ProjectService
from app.shared.runtime.errors import BusinessRuleError, NotFoundError

from .dto import (
    AnalysisCreateDTO,
    AnalysisDetailDTO,
    AnalysisSummaryDTO,
    AnalysisType,
    AnalysisUpdateDTO,
    SKILL_KEY_BLANK_MESSAGE,
)

SOURCE_TITLE_REQUIRED_MESSAGE = "source_title is required when analysis has no content reference"
LATEST_ANALYSIS_NOT_FOUND_MESSAGE = "Analysis not found for provided filters"


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
        content: Content | None = None
        if payload.content_id is not None:
            content = await self._require_project_content(db, project_id, payload.content_id)
        analysis = Analysis(
            project_id=project_id,
            content_id=payload.content_id,
            analysis_type=payload.analysis_type,
            source_title=self._resolve_source_title(payload.source_title, content),
            analysis_scope=payload.analysis_scope,
            result=payload.result,
            suggestions=payload.suggestions,
            generated_skill_key=payload.generated_skill_key,
        )
        db.add(analysis)
        await db.commit()
        await db.refresh(analysis)
        return self._to_detail(analysis)

    async def update_analysis(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        analysis_id: uuid.UUID,
        payload: AnalysisUpdateDTO,
        *,
        owner_id: uuid.UUID,
    ) -> AnalysisDetailDTO:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        analysis = await self._require_analysis(db, project_id, analysis_id)
        content = await self._load_analysis_content(db, project_id, analysis.content_id)
        self._apply_update_payload(analysis, payload, content)
        db.add(analysis)
        await db.commit()
        await db.refresh(analysis)
        return self._to_detail(analysis)

    async def delete_analysis(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        analysis_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> None:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        analysis = await self._require_analysis(db, project_id, analysis_id)
        await db.delete(analysis)
        await db.commit()

    async def list_analyses(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        analysis_type: AnalysisType | None = None,
        content_id: uuid.UUID | None = None,
        generated_skill_key: str | None = None,
        limit: int = 50,
    ) -> list[AnalysisSummaryDTO]:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        statement = await self._build_filtered_statement(
            db,
            project_id,
            analysis_type=analysis_type,
            content_id=content_id,
            generated_skill_key=generated_skill_key,
        )
        statement = self._order_latest_first(statement).limit(limit)
        analyses = (await db.scalars(statement)).all()
        return [self._to_summary(item) for item in analyses]

    async def get_latest_analysis(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        analysis_type: AnalysisType | None = None,
        content_id: uuid.UUID | None = None,
        generated_skill_key: str | None = None,
    ) -> AnalysisDetailDTO:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        statement = await self._build_filtered_statement(
            db,
            project_id,
            analysis_type=analysis_type,
            content_id=content_id,
            generated_skill_key=generated_skill_key,
        )
        analysis = await db.scalar(self._order_latest_first(statement).limit(1))
        if analysis is None:
            raise NotFoundError(LATEST_ANALYSIS_NOT_FOUND_MESSAGE)
        return self._to_detail(analysis)

    async def get_analysis(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        analysis_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> AnalysisDetailDTO:
        await self.project_service.require_project(db, project_id, owner_id=owner_id)
        analysis = await self._require_analysis(db, project_id, analysis_id)
        return self._to_detail(analysis)

    def _resolve_source_title(
        self,
        source_title: str | None,
        content: Content | None,
    ) -> str | None:
        normalized_source_title = self._normalize_optional_text(source_title)
        if normalized_source_title is not None:
            return normalized_source_title
        if content is not None:
            return self._normalize_optional_text(content.title)
        return None

    def _apply_update_payload(
        self,
        analysis: Analysis,
        payload: AnalysisUpdateDTO,
        content: Content | None,
    ) -> None:
        analysis.source_title = self._resolve_updated_source_title(analysis, payload, content)
        if "analysis_scope" in payload.model_fields_set:
            analysis.analysis_scope = payload.analysis_scope
        if "result" in payload.model_fields_set:
            analysis.result = payload.result
        if "suggestions" in payload.model_fields_set:
            analysis.suggestions = payload.suggestions
        if "generated_skill_key" in payload.model_fields_set:
            analysis.generated_skill_key = payload.generated_skill_key

    def _resolve_updated_source_title(
        self,
        analysis: Analysis,
        payload: AnalysisUpdateDTO,
        content: Content | None,
    ) -> str:
        source_title = analysis.source_title
        if "source_title" in payload.model_fields_set:
            source_title = payload.source_title
        resolved_source_title = self._resolve_source_title(source_title, content)
        if resolved_source_title is None:
            raise BusinessRuleError(SOURCE_TITLE_REQUIRED_MESSAGE)
        return resolved_source_title

    def _normalize_optional_text(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def _normalize_generated_skill_key_filter(
        self,
        generated_skill_key: str | None,
    ) -> str | None:
        normalized = self._normalize_optional_text(generated_skill_key)
        if generated_skill_key is not None and normalized is None:
            raise BusinessRuleError(SKILL_KEY_BLANK_MESSAGE)
        return normalized

    async def _build_filtered_statement(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        analysis_type: AnalysisType | None,
        content_id: uuid.UUID | None,
        generated_skill_key: str | None,
    ):
        if content_id is not None:
            await self._require_project_content(db, project_id, content_id)
        normalized_skill_key = self._normalize_generated_skill_key_filter(generated_skill_key)
        statement = select(Analysis).where(Analysis.project_id == project_id)
        if analysis_type is not None:
            statement = statement.where(Analysis.analysis_type == analysis_type)
        if content_id is not None:
            statement = statement.where(Analysis.content_id == content_id)
        if normalized_skill_key is not None:
            statement = statement.where(Analysis.generated_skill_key == normalized_skill_key)
        return statement

    def _order_latest_first(self, statement):
        return statement.order_by(Analysis.created_at.desc(), Analysis.id.desc())

    async def _require_analysis(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        analysis_id: uuid.UUID,
    ) -> Analysis:
        analysis = await db.scalar(
            select(Analysis).where(
                Analysis.id == analysis_id,
                Analysis.project_id == project_id,
            )
        )
        if analysis is None:
            raise NotFoundError(f"Analysis not found: {analysis_id}")
        return analysis

    async def _load_analysis_content(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        content_id: uuid.UUID | None,
    ) -> Content | None:
        if content_id is None:
            return None
        return await self._require_project_content(db, project_id, content_id)

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
