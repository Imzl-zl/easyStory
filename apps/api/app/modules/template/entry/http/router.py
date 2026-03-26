from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.template.service import (
    TemplateCreateDTO,
    TemplateDetailDTO,
    TemplateQueryService,
    TemplateSummaryDTO,
    TemplateUpdateDTO,
    TemplateWriteService,
    create_template_query_service,
    create_template_write_service,
)
from app.modules.user.entry.http.dependencies import get_current_user, require_control_plane_admin
from app.modules.user.models import User
from app.shared.db import get_async_db_session

router = APIRouter(prefix="/api/v1/templates", tags=["template"])


async def get_template_query_service() -> TemplateQueryService:
    return create_template_query_service()


async def get_template_write_service() -> TemplateWriteService:
    return create_template_write_service()


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


@router.post("", response_model=TemplateDetailDTO, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: TemplateCreateDTO,
    template_write_service: TemplateWriteService = Depends(get_template_write_service),
    current_user: User = Depends(require_control_plane_admin),
    db: AsyncSession = Depends(get_async_db_session),
) -> TemplateDetailDTO:
    del current_user
    return await template_write_service.create_template(db, payload)


@router.put("/{template_id}", response_model=TemplateDetailDTO)
async def update_template(
    template_id: uuid.UUID,
    payload: TemplateUpdateDTO,
    template_write_service: TemplateWriteService = Depends(get_template_write_service),
    current_user: User = Depends(require_control_plane_admin),
    db: AsyncSession = Depends(get_async_db_session),
) -> TemplateDetailDTO:
    del current_user
    return await template_write_service.update_template(db, template_id, payload)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: uuid.UUID,
    template_write_service: TemplateWriteService = Depends(get_template_write_service),
    current_user: User = Depends(require_control_plane_admin),
    db: AsyncSession = Depends(get_async_db_session),
) -> Response:
    del current_user
    await template_write_service.delete_template(db, template_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
