from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.modules.workflow.service import (
    ChapterTaskBatchDTO,
    ChapterTaskRegenerateDTO,
    ChapterTaskService,
    ChapterTaskUpdateDTO,
    ChapterTaskViewDTO,
    WorkflowAppService,
    WorkflowExecutionDTO,
    WorkflowPauseDTO,
    WorkflowStartDTO,
    create_chapter_task_service,
    create_workflow_app_service,
)
from app.shared.db import get_db_session

router = APIRouter(tags=["workflow"])


def get_workflow_app_service() -> WorkflowAppService:
    return create_workflow_app_service()


def get_chapter_task_service() -> ChapterTaskService:
    return create_chapter_task_service()


@router.post(
    "/api/v1/projects/{project_id}/workflows/start",
    response_model=WorkflowExecutionDTO,
)
def start_workflow(
    project_id: uuid.UUID,
    payload: WorkflowStartDTO | None = None,
    workflow_app_service: WorkflowAppService = Depends(get_workflow_app_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> WorkflowExecutionDTO:
    return workflow_app_service.start_workflow(
        db,
        project_id,
        payload or WorkflowStartDTO(),
        owner_id=current_user.id,
    )


@router.get("/api/v1/workflows/{workflow_id}", response_model=WorkflowExecutionDTO)
def get_workflow_detail(
    workflow_id: uuid.UUID,
    workflow_app_service: WorkflowAppService = Depends(get_workflow_app_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> WorkflowExecutionDTO:
    return workflow_app_service.get_workflow_detail(
        db,
        workflow_id,
        owner_id=current_user.id,
    )


@router.post(
    "/api/v1/workflows/{workflow_id}/pause",
    response_model=WorkflowExecutionDTO,
)
def pause_workflow(
    workflow_id: uuid.UUID,
    payload: WorkflowPauseDTO | None = None,
    workflow_app_service: WorkflowAppService = Depends(get_workflow_app_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> WorkflowExecutionDTO:
    return workflow_app_service.pause_workflow(
        db,
        workflow_id,
        payload or WorkflowPauseDTO(),
        owner_id=current_user.id,
    )


@router.post(
    "/api/v1/workflows/{workflow_id}/resume",
    response_model=WorkflowExecutionDTO,
)
def resume_workflow(
    workflow_id: uuid.UUID,
    workflow_app_service: WorkflowAppService = Depends(get_workflow_app_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> WorkflowExecutionDTO:
    return workflow_app_service.resume_workflow(
        db,
        workflow_id,
        owner_id=current_user.id,
    )


@router.post(
    "/api/v1/workflows/{workflow_id}/cancel",
    response_model=WorkflowExecutionDTO,
)
def cancel_workflow(
    workflow_id: uuid.UUID,
    workflow_app_service: WorkflowAppService = Depends(get_workflow_app_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> WorkflowExecutionDTO:
    return workflow_app_service.cancel_workflow(
        db,
        workflow_id,
        owner_id=current_user.id,
    )


@router.post(
    "/api/v1/projects/{project_id}/chapter-tasks/regenerate",
    response_model=ChapterTaskBatchDTO,
)
def regenerate_chapter_tasks(
    project_id: uuid.UUID,
    payload: ChapterTaskRegenerateDTO,
    chapter_task_service: ChapterTaskService = Depends(get_chapter_task_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ChapterTaskBatchDTO:
    return chapter_task_service.regenerate_tasks(
        db,
        project_id,
        payload,
        owner_id=current_user.id,
    )


@router.get(
    "/api/v1/workflows/{workflow_id}/chapter-tasks",
    response_model=list[ChapterTaskViewDTO],
)
def list_chapter_tasks(
    workflow_id: uuid.UUID,
    chapter_task_service: ChapterTaskService = Depends(get_chapter_task_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[ChapterTaskViewDTO]:
    return chapter_task_service.list_tasks(
        db,
        workflow_id,
        owner_id=current_user.id,
    )


@router.put(
    "/api/v1/workflows/{workflow_id}/chapter-tasks/{chapter_number}",
    response_model=ChapterTaskViewDTO,
)
def update_chapter_task(
    workflow_id: uuid.UUID,
    chapter_number: int,
    payload: ChapterTaskUpdateDTO,
    chapter_task_service: ChapterTaskService = Depends(get_chapter_task_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ChapterTaskViewDTO:
    return chapter_task_service.update_task(
        db,
        workflow_id,
        chapter_number,
        payload,
        owner_id=current_user.id,
    )
