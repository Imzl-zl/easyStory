from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.modules.content.models import Content
from app.modules.workflow.models import ChapterTask, WorkflowExecution
from app.shared.runtime.errors import BusinessRuleError

from .workflow_runtime_shared import (
    ChapterSplitPayload,
    TERMINAL_TASK_STATUSES,
    WAITING_CONFIRM_TASK_STATUS,
)


class WorkflowRuntimeTaskMixin:
    def _parse_chapter_split_output(self, raw_content: Any):
        from app.modules.workflow.service.chapter_task_dto import ChapterTaskRegenerateDTO

        payload = self._parse_json(raw_content)
        if not isinstance(payload, dict):
            raise BusinessRuleError("chapter_split 必须返回 JSON 对象")
        parsed = ChapterSplitPayload.model_validate(payload)
        normalized = [
            {
                "chapter_number": item.get("chapter_number", item.get("number")),
                "title": item.get("title"),
                "brief": item.get("brief"),
                "key_characters": item.get("key_characters", []),
                "key_events": item.get("key_events", []),
            }
            for item in parsed.chapters
        ]
        return ChapterTaskRegenerateDTO.model_validate({"chapters": normalized}).chapters

    def _parse_json(self, raw_content: Any) -> Any:
        if isinstance(raw_content, dict | list):
            return raw_content
        if not isinstance(raw_content, str):
            raise BusinessRuleError("LLM 输出必须是 JSON 字符串或对象")
        try:
            return json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise BusinessRuleError("LLM 输出不是合法 JSON") from exc

    def _replace_chapter_tasks(self, db: Session, workflow: WorkflowExecution, chapters) -> None:
        db.query(ChapterTask).filter(ChapterTask.workflow_execution_id == workflow.id).delete(
            synchronize_session=False
        )
        db.flush()
        for chapter in chapters:
            db.add(
                ChapterTask(
                    project_id=workflow.project_id,
                    workflow_execution_id=workflow.id,
                    chapter_number=chapter.chapter_number,
                    title=chapter.title,
                    brief=chapter.brief,
                    key_characters=list(chapter.key_characters),
                    key_events=list(chapter.key_events),
                    status="pending",
                )
            )

    def _next_actionable_task(self, db: Session, workflow: WorkflowExecution) -> ChapterTask | None:
        tasks = (
            db.query(ChapterTask)
            .filter(ChapterTask.workflow_execution_id == workflow.id)
            .order_by(ChapterTask.chapter_number.asc())
            .all()
        )
        return next((task for task in tasks if task.status not in TERMINAL_TASK_STATUSES), None)

    def _ensure_task_can_continue(self, db: Session, task: ChapterTask) -> None:
        if task.status == "stale":
            raise BusinessRuleError("当前章节任务已失效，请先重新执行 chapter_split")
        if task.status not in {WAITING_CONFIRM_TASK_STATUS, "failed"}:
            return
        if task.content_id is None:
            if task.status == "failed":
                return
            raise BusinessRuleError("当前章节草稿待确认，请先确认或修改后再继续")
        content = db.get(Content, task.content_id)
        if content is None or content.status != "approved":
            raise BusinessRuleError("当前章节草稿待确认，请先确认或修改后再继续")

    def _hash_payload(self, payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        import hashlib

        return hashlib.sha256(raw).hexdigest()

    def _stringify_value(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)

    def _serialize_replay_text(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
