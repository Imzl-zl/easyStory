from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.user.entry.http.dependencies import get_current_user
from app.modules.user.models import User
from app.modules.workflow.service import (
    ChapterTaskBatchDTO,
    ChapterTaskService,
    ChapterTaskRegenerateDTO,
    ChapterTaskUpdateDTO,
    ChapterTaskViewDTO,
    WorkflowAppService,
    WorkflowExecutionDTO,
    WorkflowExecutionStatus,
    WorkflowExecutionSummaryDTO,
    WorkflowPauseDTO,
    WorkflowStartDTO,
    create_chapter_task_service,
    create_workflow_app_service,
)
from app.shared.db import AsyncSessionFactory, get_async_db_session, get_async_session_factory

router = APIRouter(tags=["workflow"])
WorkflowRuntimeDispatcher = Callable[[uuid.UUID, uuid.UUID], None]
logger = logging.getLogger(__name__)


async def get_workflow_app_service() -> WorkflowAppService:
    return create_workflow_app_service()


async def get_chapter_task_service() -> ChapterTaskService:
    return create_chapter_task_service()


async def get_workflow_runtime_dispatcher(
    request: Request,
    workflow_app_service: WorkflowAppService = Depends(get_workflow_app_service),
) -> WorkflowRuntimeDispatcher:
    session_factory = get_async_session_factory(request)

    def dispatch(workflow_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        task = asyncio.create_task(
            _run_workflow_runtime(workflow_app_service, session_factory, workflow_id, owner_id)
        )
        task.add_done_callback(_log_runtime_dispatch_failure)

    return dispatch


@router.post(
    "/api/v1/projects/{project_id}/workflows/start",
    response_model=WorkflowExecutionDTO,
)
async def start_workflow(
    project_id: uuid.UUID,
    payload: WorkflowStartDTO | None = None,
    workflow_app_service: WorkflowAppService = Depends(get_workflow_app_service),
    runtime_dispatcher: WorkflowRuntimeDispatcher = Depends(get_workflow_runtime_dispatcher),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> WorkflowExecutionDTO:
    return await workflow_app_service.start_workflow(
        db,
        project_id,
        payload or WorkflowStartDTO(),
        owner_id=current_user.id,
        runtime_dispatcher=runtime_dispatcher,
    )


@router.get(
    "/api/v1/projects/{project_id}/workflows",
    response_model=list[WorkflowExecutionSummaryDTO],
)
async def list_project_workflows(
    project_id: uuid.UUID,
    status: WorkflowExecutionStatus | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    workflow_app_service: WorkflowAppService = Depends(get_workflow_app_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> list[WorkflowExecutionSummaryDTO]:
    return await workflow_app_service.list_project_workflows(
        db,
        project_id,
        owner_id=current_user.id,
        status=status,
        limit=limit,
    )


@router.get("/api/v1/workflows/{workflow_id}", response_model=WorkflowExecutionDTO)
async def get_workflow_detail(
    workflow_id: uuid.UUID,
    workflow_app_service: WorkflowAppService = Depends(get_workflow_app_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> WorkflowExecutionDTO:
    return await workflow_app_service.get_workflow_detail(
        db,
        workflow_id,
        owner_id=current_user.id,
    )


@router.post(
    "/api/v1/workflows/{workflow_id}/pause",
    response_model=WorkflowExecutionDTO,
)
async def pause_workflow(
    workflow_id: uuid.UUID,
    payload: WorkflowPauseDTO | None = None,
    workflow_app_service: WorkflowAppService = Depends(get_workflow_app_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> WorkflowExecutionDTO:
    return await workflow_app_service.pause_workflow(
        db,
        workflow_id,
        payload or WorkflowPauseDTO(),
        owner_id=current_user.id,
    )


@router.post(
    "/api/v1/workflows/{workflow_id}/resume",
    response_model=WorkflowExecutionDTO,
)
async def resume_workflow(
    workflow_id: uuid.UUID,
    workflow_app_service: WorkflowAppService = Depends(get_workflow_app_service),
    runtime_dispatcher: WorkflowRuntimeDispatcher = Depends(get_workflow_runtime_dispatcher),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> WorkflowExecutionDTO:
    return await workflow_app_service.resume_workflow(
        db,
        workflow_id,
        owner_id=current_user.id,
        runtime_dispatcher=runtime_dispatcher,
    )


@router.post(
    "/api/v1/workflows/{workflow_id}/cancel",
    response_model=WorkflowExecutionDTO,
)
async def cancel_workflow(
    workflow_id: uuid.UUID,
    workflow_app_service: WorkflowAppService = Depends(get_workflow_app_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> WorkflowExecutionDTO:
    return await workflow_app_service.cancel_workflow(
        db,
        workflow_id,
        owner_id=current_user.id,
    )


@router.post(
    "/api/v1/projects/{project_id}/chapter-tasks/regenerate",
    response_model=ChapterTaskBatchDTO,
)
async def regenerate_chapter_tasks(
    project_id: uuid.UUID,
    payload: ChapterTaskRegenerateDTO,
    chapter_task_service: ChapterTaskService = Depends(get_chapter_task_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ChapterTaskBatchDTO:
    return await chapter_task_service.regenerate_tasks(
        db,
        project_id,
        payload,
        owner_id=current_user.id,
    )


@router.get(
    "/api/v1/workflows/{workflow_id}/chapter-tasks",
    response_model=list[ChapterTaskViewDTO],
)
async def list_chapter_tasks(
    workflow_id: uuid.UUID,
    chapter_task_service: ChapterTaskService = Depends(get_chapter_task_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> list[ChapterTaskViewDTO]:
    return await chapter_task_service.list_tasks(
        db,
        workflow_id,
        owner_id=current_user.id,
    )


@router.put(
    "/api/v1/workflows/{workflow_id}/chapter-tasks/{chapter_number}",
    response_model=ChapterTaskViewDTO,
)
async def update_chapter_task(
    workflow_id: uuid.UUID,
    chapter_number: int,
    payload: ChapterTaskUpdateDTO,
    chapter_task_service: ChapterTaskService = Depends(get_chapter_task_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ChapterTaskViewDTO:
    return await chapter_task_service.update_task(
        db,
        workflow_id,
        chapter_number,
        payload,
        owner_id=current_user.id,
    )


async def _run_workflow_runtime(
    workflow_app_service: WorkflowAppService,
    session_factory: AsyncSessionFactory,
    workflow_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> None:
    async with session_factory() as session:
        await workflow_app_service.run_workflow_runtime(
            session,
            workflow_id,
            owner_id=owner_id,
        )


def _log_runtime_dispatch_failure(task: asyncio.Task[None]) -> None:
    try:
        exception = task.exception()
    except asyncio.CancelledError:
        logger.warning("Workflow runtime task was cancelled")
        return
    if exception is not None:
        logger.error(
            "Workflow runtime task failed",
            exc_info=(type(exception), exception, exception.__traceback__),
        )
