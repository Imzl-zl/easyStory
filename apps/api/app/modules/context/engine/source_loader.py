from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.modules.content.models import Content
from app.modules.context.models import StoryFact
from app.modules.project.models import Project
from app.modules.workflow.models import ChapterTask

from .contracts import (
    CHAPTER_SEPARATOR,
    OPENING_PLAN_DEGRADED_MAX_CHARS,
    OPENING_PLAN_PRIORITY_CHAPTER_LIMIT,
)

ContextPayload = tuple[str, str, dict[str, Any]]
APPROVED_CONTENT_TYPES = frozenset({"outline", "opening_plan"})
UNAVAILABLE_CHAPTER_TASK_STATUSES = frozenset({"stale", "skipped"})


class ContextSourceLoader:
    def load_content(
        self,
        project_id,
        inject_type: str,
        db: Session,
        *,
        chapter_number: int | None,
        workflow_execution_id,
        count: int | None,
    ) -> ContextPayload:
        if inject_type == "project_setting":
            return self._load_project_setting(project_id, db)
        if inject_type == "outline":
            return self._load_single_content(project_id, db, "outline")
        if inject_type == "opening_plan":
            return self._load_opening_plan(project_id, db, chapter_number)
        if inject_type == "chapter_task":
            return self._load_chapter_task(project_id, db, workflow_execution_id, chapter_number)
        if inject_type == "previous_chapters":
            return self._load_previous_chapters(project_id, db, chapter_number, count or 2)
        if inject_type == "story_bible":
            return self._load_story_bible(project_id, db, chapter_number)
        raise ValueError(f"Unsupported inject type: {inject_type}")

    def _load_project_setting(self, project_id, db: Session) -> ContextPayload:
        project = db.query(Project).filter(Project.id == project_id).one_or_none()
        if project is None or project.project_setting is None:
            return "", "missing", {}
        return self._dump_json(project.project_setting), "included", {}

    def _load_single_content(
        self,
        project_id,
        db: Session,
        content_type: str,
    ) -> ContextPayload:
        content = self._get_project_content(db, project_id, content_type)
        if content is None:
            return "", "missing", {}
        if not self._is_injectable_content(content_type, content):
            return "", "missing", {"content_status": content.status}
        text = self._get_current_version_text(content)
        if not text:
            return "", "missing", {}
        metadata: dict[str, Any] = {}
        if content_type == "outline" and content.chapter_number is not None:
            metadata["chapter_number"] = content.chapter_number
        return text, "included", metadata

    def _load_opening_plan(
        self,
        project_id,
        db: Session,
        chapter_number: int | None,
    ) -> ContextPayload:
        text, status, metadata = self._load_single_content(project_id, db, "opening_plan")
        if not text or chapter_number is None or chapter_number <= OPENING_PLAN_PRIORITY_CHAPTER_LIMIT:
            return text, status, metadata
        degraded = text[:OPENING_PLAN_DEGRADED_MAX_CHARS].rstrip()
        if len(degraded) < len(text):
            degraded += "\n..."
        summary = "开篇设计摘要（第 4 章后降级引用）：\n" + degraded
        metadata["phase"] = "degraded_reference"
        return summary, "degraded", metadata

    def _load_chapter_task(
        self,
        project_id,
        db: Session,
        workflow_execution_id,
        chapter_number: int | None,
    ) -> ContextPayload:
        if workflow_execution_id is None or chapter_number is None:
            return "", "missing", {}
        if not self._has_approved_content(db, project_id, "outline"):
            return "", "missing", {"missing_dependency": "outline"}
        if not self._has_approved_content(db, project_id, "opening_plan"):
            return "", "missing", {"missing_dependency": "opening_plan"}
        task = (
            db.query(ChapterTask)
            .filter(
                ChapterTask.project_id == project_id,
                ChapterTask.workflow_execution_id == workflow_execution_id,
                ChapterTask.chapter_number == chapter_number,
            )
            .one_or_none()
        )
        if task is None:
            return "", "missing", {}
        if task.status in UNAVAILABLE_CHAPTER_TASK_STATUSES:
            return "", "missing", {"task_status": task.status}
        lines = [f"标题：{task.title}", f"概要：{task.brief}"]
        if task.key_characters:
            lines.append("关键角色：" + "、".join(task.key_characters))
        if task.key_events:
            lines.append("关键事件：" + "、".join(task.key_events))
        return "\n".join(lines), "included", {"chapter_number": task.chapter_number}

    def _load_previous_chapters(
        self,
        project_id,
        db: Session,
        chapter_number: int | None,
        count: int,
    ) -> ContextPayload:
        if chapter_number is None or chapter_number <= 1:
            return "", "not_applicable", {"chapters": []}
        chapters = self._get_recent_chapters(db, project_id, chapter_number, count)
        if not chapters:
            return "", "not_applicable", {"chapters": []}
        parts, numbers = self._format_chapter_context(chapters)
        if not parts:
            return "", "not_applicable", {"chapters": []}
        return CHAPTER_SEPARATOR.join(parts), "included", {"chapters": numbers}

    def _get_recent_chapters(
        self,
        db: Session,
        project_id,
        chapter_number: int,
        count: int,
    ) -> list[Content]:
        chapters = (
            db.query(Content)
            .filter(
                Content.project_id == project_id,
                Content.content_type == "chapter",
                Content.chapter_number < chapter_number,
            )
            .order_by(Content.chapter_number.desc())
            .limit(count)
            .all()
        )
        return sorted(chapters, key=lambda item: item.chapter_number or 0)

    def _format_chapter_context(
        self,
        chapters: list[Content],
    ) -> tuple[list[str], list[int]]:
        parts: list[str] = []
        numbers: list[int] = []
        for chapter in chapters:
            text = self._get_current_version_text(chapter)
            if not text or chapter.chapter_number is None:
                continue
            numbers.append(chapter.chapter_number)
            parts.append(f"第{chapter.chapter_number}章 {chapter.title}\n{text}")
        return parts, numbers

    def _load_story_bible(
        self,
        project_id,
        db: Session,
        chapter_number: int | None,
    ) -> ContextPayload:
        facts = db.query(StoryFact).filter(
            StoryFact.project_id == project_id,
            StoryFact.is_active.is_(True),
            StoryFact.superseded_by.is_(None),
            StoryFact.conflict_status != "confirmed",
        )
        if chapter_number is not None:
            facts = facts.filter(StoryFact.chapter_number <= chapter_number)
        entries = facts.order_by(StoryFact.chapter_number.asc(), StoryFact.fact_type.asc()).all()
        if not entries:
            return "", "not_applicable", {"items_count": 0}
        return self._render_story_bible(entries), "included", {"items_count": len(entries)}

    def _render_story_bible(self, facts: list[StoryFact]) -> str:
        grouped: dict[str, list[str]] = {}
        for fact in facts:
            grouped.setdefault(fact.fact_type, []).append(f"{fact.subject}：{fact.content}")
        lines = []
        for fact_type, items in grouped.items():
            section = f"[{fact_type}]\n" + "\n".join(f"- {item}" for item in items)
            lines.append(section)
        return "\n\n".join(lines)

    def _get_project_content(self, db: Session, project_id, content_type: str) -> Content | None:
        return (
            db.query(Content)
            .filter(Content.project_id == project_id, Content.content_type == content_type)
            .one_or_none()
        )

    def _is_injectable_content(self, content_type: str, content: Content) -> bool:
        if content_type not in APPROVED_CONTENT_TYPES:
            return True
        return content.status == "approved"

    def _has_approved_content(self, db: Session, project_id, content_type: str) -> bool:
        content = self._get_project_content(db, project_id, content_type)
        if content is None or content.status != "approved":
            return False
        return bool(self._get_current_version_text(content))

    def _get_current_version_text(self, content: Content) -> str | None:
        versions = sorted(content.versions, key=lambda item: (item.is_current, item.version_number), reverse=True)
        return versions[0].content_text if versions else None

    def _dump_json(self, value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
