from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.export.service import (
    ExportCreateDTO,
    ExportService,
    ExportViewDTO,
    create_export_service,
)
from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.shared.db import get_async_db_session

router = APIRouter(tags=["exports"])


def get_export_service() -> ExportService:
    return create_export_service()


@router.get("/api/v1/projects/{project_id}/exports", response_model=list[ExportViewDTO])
async def list_project_exports(
    project_id: uuid.UUID,
    export_service: ExportService = Depends(get_export_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> list[ExportViewDTO]:
    exports = await export_service.list_project_exports(
        db,
        project_id,
        owner_id=current_user.id,
    )
    return [export_service.to_view_dto(item) for item in exports]


@router.post("/api/v1/workflows/{workflow_id}/exports", response_model=list[ExportViewDTO])
async def create_workflow_exports(
    workflow_id: uuid.UUID,
    payload: ExportCreateDTO | None = None,
    export_service: ExportService = Depends(get_export_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> list[ExportViewDTO]:
    exports = await export_service.create_workflow_exports(
        db,
        workflow_id,
        formats=(payload or ExportCreateDTO()).formats,
        owner_id=current_user.id,
    )
    return [export_service.to_view_dto(item) for item in exports]


@router.get("/api/v1/exports/{export_id}/download")
async def download_export(
    export_id: uuid.UUID,
    export_service: ExportService = Depends(get_export_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> FileResponse:
    export, file_path = await export_service.resolve_download(
        db,
        export_id,
        owner_id=current_user.id,
    )
    media_type = "text/markdown" if export.format == "markdown" else "text/plain"
    return FileResponse(
        path=file_path,
        filename=export.filename,
        media_type=media_type,
    )
