from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analysis.service import (
    AnalysisCreateDTO,
    AnalysisDetailDTO,
    AnalysisService,
    AnalysisType,
    AnalysisSummaryDTO,
    create_analysis_service,
)
from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.shared.db import get_async_db_session

router = APIRouter(prefix="/api/v1/projects/{project_id}/analyses", tags=["analysis"])


async def get_analysis_service() -> AnalysisService:
    return create_analysis_service()


@router.post("", response_model=AnalysisDetailDTO)
async def create_analysis(
    project_id: uuid.UUID,
    payload: AnalysisCreateDTO,
    analysis_service: AnalysisService = Depends(get_analysis_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AnalysisDetailDTO:
    return await analysis_service.create_analysis(
        db,
        project_id,
        payload,
        owner_id=current_user.id,
    )


@router.get("", response_model=list[AnalysisSummaryDTO])
async def list_analyses(
    project_id: uuid.UUID,
    analysis_type: AnalysisType | None = Query(default=None),
    content_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    analysis_service: AnalysisService = Depends(get_analysis_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> list[AnalysisSummaryDTO]:
    return await analysis_service.list_analyses(
        db,
        project_id,
        owner_id=current_user.id,
        analysis_type=analysis_type,
        content_id=content_id,
        limit=limit,
    )


@router.get("/{analysis_id}", response_model=AnalysisDetailDTO)
async def get_analysis(
    project_id: uuid.UUID,
    analysis_id: uuid.UUID,
    analysis_service: AnalysisService = Depends(get_analysis_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> AnalysisDetailDTO:
    return await analysis_service.get_analysis(
        db,
        project_id,
        analysis_id,
        owner_id=current_user.id,
    )
