from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.template.service import (
    TemplateDetailDTO,
    TemplateQueryService,
    TemplateSummaryDTO,
    create_template_query_service,
)
from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.shared.db import get_async_db_session

router = APIRouter(prefix="/api/v1/templates", tags=["template"])


async def get_template_query_service() -> TemplateQueryService:
    return create_template_query_service()


@router.get("", response_model=list[TemplateSummaryDTO])
async def list_templates(
    template_query_service: TemplateQueryService = Depends(get_template_query_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> list[TemplateSummaryDTO]:
    del current_user
    return await template_query_service.list_templates(db)


@router.get("/{template_id}", response_model=TemplateDetailDTO)
async def get_template(
    template_id: uuid.UUID,
    template_query_service: TemplateQueryService = Depends(get_template_query_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> TemplateDetailDTO:
    del current_user
    return await template_query_service.get_template(db, template_id)
