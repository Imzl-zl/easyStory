from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.workflow.models import ChapterTask, WorkflowExecution
from app.shared.runtime.errors import BusinessRuleError

from .workflow_runtime_shared import ChapterSplitPayload
from .workflow_task_runtime_support import ensure_task_can_continue, find_next_actionable_task


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

    async def _replace_chapter_tasks(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        chapters,
    ) -> None:
        await db.execute(
            delete(ChapterTask).where(ChapterTask.workflow_execution_id == workflow.id)
        )
        await db.flush()
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

    async def _next_actionable_task(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
    ) -> ChapterTask | None:
        return await find_next_actionable_task(db, workflow.id)

    async def _ensure_task_can_continue(
        self,
        db: AsyncSession,
        task: ChapterTask,
    ) -> None:
        await ensure_task_can_continue(db, task)

    def _hash_payload(self, payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
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
