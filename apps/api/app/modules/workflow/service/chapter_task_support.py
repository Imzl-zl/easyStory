from __future__ import annotations

from app.modules.workflow.models import ChapterTask, WorkflowExecution

from .chapter_task_dto import ChapterTaskUpdateDTO, ChapterTaskViewDTO
from .snapshot_support import resolve_next_node_id

PREPARATION_ASSET_LABELS = {
    "outline": "大纲",
    "opening_plan": "开篇设计",
}
EDITABLE_CHAPTER_TASK_STATUSES = frozenset({"pending", "generating", "failed", "interrupted"})


def advance_workflow_after_regenerate(workflow: WorkflowExecution) -> None:
    next_node_id = resolve_next_node_id(
        workflow.workflow_snapshot or {},
        current_node_id="chapter_split",
    )
    if next_node_id is None:
        return
    workflow.current_node_id = next_node_id
    if workflow.status == "paused":
        workflow.resume_from_node = next_node_id


def ensure_task_editable(task: ChapterTask) -> None:
    from app.shared.runtime.errors import BusinessRuleError

    if task.status == "stale":
        raise BusinessRuleError("当前章节任务已 stale，必须先重建章节计划后才能编辑")
    if task.status not in EDITABLE_CHAPTER_TASK_STATUSES:
        raise BusinessRuleError(f"当前章节任务状态不允许编辑: {task.status}")


def apply_task_update(
    task: ChapterTask,
    payload: ChapterTaskUpdateDTO,
) -> None:
    if payload.title is not None:
        task.title = payload.title.strip()
    if payload.brief is not None:
        task.brief = payload.brief.strip()
    if payload.key_characters is not None:
        task.key_characters = list(payload.key_characters)
    if payload.key_events is not None:
        task.key_events = list(payload.key_events)


def to_view(task: ChapterTask) -> ChapterTaskViewDTO:
    return ChapterTaskViewDTO(
        task_id=task.id,
        project_id=task.project_id,
        workflow_execution_id=task.workflow_execution_id,
        chapter_number=task.chapter_number,
        title=task.title,
        brief=task.brief,
        key_characters=list(task.key_characters or []),
        key_events=list(task.key_events or []),
        status=task.status,
        content_id=task.content_id,
    )
