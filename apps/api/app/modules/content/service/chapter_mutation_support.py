from __future__ import annotations

import uuid

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.modules.project.models import Project
from app.modules.workflow.models import ChapterTask, WorkflowExecution

from .chapter_service_support import CHAPTER_TYPE

WAITING_CONFIRM_TASK_STATUS = "generating"
FAILED_TASK_STATUS = "failed"
ACTIVE_WORKFLOW_STATUSES = ("running", "paused")
FAILED_WORKFLOW_STATUSES = ("failed",)


def mark_downstream_chapters_stale(project: Project, chapter_number: int) -> None:
    for content in project.contents:
        if content.content_type != CHAPTER_TYPE:
            continue
        if content.chapter_number is None or content.chapter_number <= chapter_number:
            continue
        if content.status == "approved":
            content.status = "stale"


def mark_active_chapter_task_completed(
    db: Session,
    project_id: uuid.UUID,
    chapter_number: int,
    content_id: uuid.UUID,
) -> None:
    task = _find_matching_task(
        db,
        project_id,
        chapter_number,
        content_id,
        task_statuses=(WAITING_CONFIRM_TASK_STATUS,),
        workflow_statuses=ACTIVE_WORKFLOW_STATUSES,
        allow_empty_content=True,
    )
    if task is None:
        task = _find_matching_task(
            db,
            project_id,
            chapter_number,
            content_id,
            task_statuses=(FAILED_TASK_STATUS,),
            workflow_statuses=FAILED_WORKFLOW_STATUSES,
            allow_empty_content=False,
        )
    if task is None:
        return
    task.content_id = content_id
    task.status = "completed"


def _find_matching_task(
    db: Session,
    project_id: uuid.UUID,
    chapter_number: int,
    content_id: uuid.UUID,
    *,
    task_statuses: tuple[str, ...],
    workflow_statuses: tuple[str, ...],
    allow_empty_content: bool,
) -> ChapterTask | None:
    content_filter = ChapterTask.content_id == content_id
    if allow_empty_content:
        content_filter = or_(ChapterTask.content_id.is_(None), content_filter)
    return (
        db.query(ChapterTask)
        .join(WorkflowExecution, ChapterTask.workflow_execution_id == WorkflowExecution.id)
        .filter(
            ChapterTask.project_id == project_id,
            ChapterTask.chapter_number == chapter_number,
            ChapterTask.status.in_(task_statuses),
            WorkflowExecution.status.in_(workflow_statuses),
            content_filter,
        )
        .order_by(WorkflowExecution.updated_at.desc())
        .first()
    )
