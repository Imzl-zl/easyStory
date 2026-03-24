from __future__ import annotations

import uuid

from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.project.models import Project
from app.modules.workflow.models import ChapterTask, WorkflowExecution

from .chapter_service_support import CHAPTER_TYPE
from .dto import ChapterImpactItemDTO, ChapterImpactSummaryDTO

WAITING_CONFIRM_TASK_STATUS = "generating"
FAILED_TASK_STATUS = "failed"
ACTIVE_WORKFLOW_STATUSES = ("running", "paused")
FAILED_WORKFLOW_STATUSES = ("failed",)
CHAPTER_IMPACT_TARGET = "chapter"


def mark_downstream_chapters_stale(project: Project, chapter_number: int) -> int:
    stale_count = 0
    for content in project.contents:
        if content.content_type != CHAPTER_TYPE:
            continue
        if content.chapter_number is None or content.chapter_number <= chapter_number:
            continue
        if content.status == "approved":
            content.status = "stale"
            stale_count += 1
    return stale_count


def build_chapter_impact_summary(stale_chapter_count: int) -> ChapterImpactSummaryDTO:
    if stale_chapter_count == 0:
        return ChapterImpactSummaryDTO()
    return ChapterImpactSummaryDTO(
        has_impact=True,
        total_affected_entries=stale_chapter_count,
        items=[
            ChapterImpactItemDTO(
                target=CHAPTER_IMPACT_TARGET,
                action="mark_stale",
                count=stale_chapter_count,
                message=format_chapter_impact_message(stale_chapter_count),
            )
        ],
    )


def format_chapter_impact_message(count: int) -> str:
    return f"{count} 个后续已确认章节已标记为 stale，需要按范围复核正文"


async def mark_active_chapter_task_completed(
    db: AsyncSession,
    project_id: uuid.UUID,
    chapter_number: int,
    content_id: uuid.UUID,
) -> None:
    task = await _find_matching_task(
        db,
        project_id,
        chapter_number,
        content_id,
        task_statuses=(WAITING_CONFIRM_TASK_STATUS,),
        workflow_statuses=ACTIVE_WORKFLOW_STATUSES,
        allow_empty_content=True,
    )
    if task is None:
        task = await _find_matching_task(
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


async def _find_matching_task(
    db: AsyncSession,
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
    statement = (
        select(ChapterTask)
        .join(WorkflowExecution, ChapterTask.workflow_execution_id == WorkflowExecution.id)
        .where(
            ChapterTask.project_id == project_id,
            ChapterTask.chapter_number == chapter_number,
            ChapterTask.status.in_(task_statuses),
            WorkflowExecution.status.in_(workflow_statuses),
            content_filter,
        )
        .order_by(WorkflowExecution.updated_at.desc())
        .limit(1)
    )
    return await db.scalar(statement)
