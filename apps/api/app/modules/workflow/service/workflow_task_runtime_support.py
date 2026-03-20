from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.modules.content.models import Content
from app.modules.workflow.models import ChapterTask
from app.shared.runtime.errors import BusinessRuleError

from .workflow_runtime_shared import TERMINAL_TASK_STATUSES, WAITING_CONFIRM_TASK_STATUS

CONFIRMATION_REQUIRED_TASK_STATUSES = frozenset({WAITING_CONFIRM_TASK_STATUS, "failed"})
STALE_CHAPTER_TASK_STATUS = "stale"
WAITING_CONFIRM_MESSAGE = "当前章节草稿待确认，请先确认或修改后再继续"


def find_next_actionable_task(db: Session, workflow_id: uuid.UUID) -> ChapterTask | None:
    tasks = (
        db.query(ChapterTask)
        .filter(ChapterTask.workflow_execution_id == workflow_id)
        .order_by(ChapterTask.chapter_number.asc())
        .all()
    )
    return next((task for task in tasks if task.status not in TERMINAL_TASK_STATUSES), None)


def ensure_task_can_continue(db: Session, task: ChapterTask) -> None:
    if task.status == STALE_CHAPTER_TASK_STATUS:
        raise BusinessRuleError("当前章节任务已失效，请先重新执行 chapter_split")
    if task.status not in CONFIRMATION_REQUIRED_TASK_STATUSES:
        return
    if _task_requires_confirmation(db, task):
        raise BusinessRuleError(WAITING_CONFIRM_MESSAGE)


def ensure_workflow_can_resume(db: Session, workflow_id: uuid.UUID) -> None:
    task = find_next_actionable_task(db, workflow_id)
    if task is None:
        return
    ensure_task_can_continue(db, task)


def _task_requires_confirmation(db: Session, task: ChapterTask) -> bool:
    if task.content_id is None:
        return task.status != "failed"
    content = db.get(Content, task.content_id)
    return content is None or content.status != "approved"
