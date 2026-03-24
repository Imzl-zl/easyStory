from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.analysis.models import Analysis
from app.modules.content.models import Content
from app.modules.context.models import StoryFact
from app.modules.project.models import Project
from app.modules.project.schemas import ProjectSettingProjectionError, build_setting_projection
from app.modules.workflow.models import ChapterTask

from .contracts import (
    CHAPTER_SEPARATOR,
    OPENING_PLAN_DEGRADED_MAX_CHARS,
    OPENING_PLAN_PRIORITY_CHAPTER_LIMIT,
)
from .errors import ContextBuilderError
from .source_loader_support import (
    CHAPTER_SUMMARY_MODE,
    CHAPTER_SUMMARY_SEPARATOR,
    DEFAULT_CHAPTER_SUMMARY_COUNT,
    build_chapter_summaries,
    dump_json,
    ensure_style_reference_analysis_type,
    format_chapter_context,
    get_current_version_text,
    render_story_bible,
    render_style_reference,
    select_style_reference_fields,
)

ContextPayload = tuple[str, str, dict[str, Any]]
APPROVED_CONTENT_TYPES = frozenset({"outline", "opening_plan"})
UNAVAILABLE_CHAPTER_TASK_STATUSES = frozenset({"stale", "skipped"})


class ContextSourceLoader:
    async def load_content(
        self,
        project_id,
        inject_type: str,
        db: AsyncSession,
        *,
        chapter_number: int | None,
        workflow_execution_id,
        count: int | None,
        analysis_id,
        inject_fields: list[str],
    ) -> ContextPayload:
        if inject_type == "project_setting":
            return await self._load_project_setting(project_id, db)
        if inject_type == "outline":
            return await self._load_single_content(project_id, db, "outline")
        if inject_type == "opening_plan":
            return await self._load_opening_plan(project_id, db, chapter_number)
        if inject_type in {"world_setting", "character_profile"}:
            return await self._load_setting_projection(project_id, db, inject_type)
        if inject_type == "chapter_task":
            return await self._load_chapter_task(project_id, db, workflow_execution_id, chapter_number)
        if inject_type == "previous_chapters":
            return await self._load_previous_chapters(project_id, db, chapter_number, count or 2)
        if inject_type == "chapter_summary":
            summary_count = count if count is not None else DEFAULT_CHAPTER_SUMMARY_COUNT
            return await self._load_chapter_summary(project_id, db, chapter_number, summary_count)
        if inject_type == "story_bible":
            return await self._load_story_bible(project_id, db, chapter_number)
        if inject_type == "style_reference":
            return await self._load_style_reference(project_id, db, analysis_id, inject_fields)
        raise ValueError(f"Unsupported inject type: {inject_type}")

    async def _load_project_setting(self, project_id, db: AsyncSession) -> ContextPayload:
        project = await db.get(Project, project_id)
        if project is None or project.project_setting is None:
            return "", "missing", {}
        return dump_json(project.project_setting), "included", {}

    async def _load_setting_projection(
        self,
        project_id,
        db: AsyncSession,
        inject_type: str,
    ) -> ContextPayload:
        project = await db.get(Project, project_id)
        if project is None or project.project_setting is None:
            return "", "missing", {}
        content, metadata = self._build_setting_projection(project.project_setting, inject_type)
        if not content:
            return "", "missing", metadata
        return content, "included", metadata

    def _build_setting_projection(
        self,
        setting_payload: dict[str, Any],
        inject_type: str,
    ) -> tuple[str, dict[str, Any]]:
        try:
            return build_setting_projection(setting_payload, inject_type)
        except ProjectSettingProjectionError as exc:
            raise ContextBuilderError(str(exc)) from exc

    async def _load_single_content(
        self,
        project_id,
        db: AsyncSession,
        content_type: str,
    ) -> ContextPayload:
        content = await self._get_project_content(db, project_id, content_type)
        if content is None:
            return "", "missing", {}
        if not self._is_injectable_content(content_type, content):
            return "", "missing", {"content_status": content.status}
        text = get_current_version_text(content)
        if not text:
            return "", "missing", {}
        metadata: dict[str, Any] = {}
        if content_type == "outline" and content.chapter_number is not None:
            metadata["chapter_number"] = content.chapter_number
        return text, "included", metadata

    async def _load_opening_plan(
        self,
        project_id,
        db: AsyncSession,
        chapter_number: int | None,
    ) -> ContextPayload:
        text, status, metadata = await self._load_single_content(project_id, db, "opening_plan")
        if not text or chapter_number is None or chapter_number <= OPENING_PLAN_PRIORITY_CHAPTER_LIMIT:
            return text, status, metadata
        degraded = text[:OPENING_PLAN_DEGRADED_MAX_CHARS].rstrip()
        if len(degraded) < len(text):
            degraded += "\n..."
        summary = "开篇设计摘要（第 4 章后降级引用）：\n" + degraded
        metadata["phase"] = "degraded_reference"
        return summary, "degraded", metadata

    async def _load_chapter_task(
        self,
        project_id,
        db: AsyncSession,
        workflow_execution_id,
        chapter_number: int | None,
    ) -> ContextPayload:
        if workflow_execution_id is None or chapter_number is None:
            return "", "missing", {}
        if not await self._has_approved_content(db, project_id, "outline"):
            return "", "missing", {"missing_dependency": "outline"}
        if not await self._has_approved_content(db, project_id, "opening_plan"):
            return "", "missing", {"missing_dependency": "opening_plan"}
        task = await db.scalar(
            select(ChapterTask).where(
                ChapterTask.project_id == project_id,
                ChapterTask.workflow_execution_id == workflow_execution_id,
                ChapterTask.chapter_number == chapter_number,
            )
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

    async def _load_previous_chapters(
        self,
        project_id,
        db: AsyncSession,
        chapter_number: int | None,
        count: int,
    ) -> ContextPayload:
        if chapter_number is None or chapter_number <= 1:
            return "", "not_applicable", {"chapters": []}
        chapters = await self._get_recent_chapters(db, project_id, chapter_number, count)
        if not chapters:
            return "", "not_applicable", {"chapters": []}
        parts, numbers = format_chapter_context(chapters)
        if not parts:
            return "", "not_applicable", {"chapters": []}
        return CHAPTER_SEPARATOR.join(parts), "included", {"chapters": numbers}

    async def _load_chapter_summary(
        self,
        project_id,
        db: AsyncSession,
        chapter_number: int | None,
        count: int,
    ) -> ContextPayload:
        if chapter_number is None or chapter_number <= 1:
            return "", "not_applicable", {"chapters": []}
        chapters = await self._get_recent_chapters(db, project_id, chapter_number, count)
        if not chapters:
            return "", "not_applicable", {"chapters": []}
        summaries, numbers = build_chapter_summaries(chapters)
        if not summaries:
            return "", "not_applicable", {"chapters": []}
        return CHAPTER_SUMMARY_SEPARATOR.join(summaries), "included", {
            "chapters": numbers,
            "summary_mode": CHAPTER_SUMMARY_MODE,
        }

    async def _get_recent_chapters(
        self,
        db: AsyncSession,
        project_id,
        chapter_number: int,
        count: int,
    ) -> list[Content]:
        statement = (
            select(Content)
            .options(selectinload(Content.versions))
            .where(
                Content.project_id == project_id,
                Content.content_type == "chapter",
                Content.chapter_number < chapter_number,
            )
            .order_by(Content.chapter_number.desc())
            .limit(count)
        )
        chapters = (await db.scalars(statement)).all()
        return sorted(chapters, key=lambda item: item.chapter_number or 0)

    async def _load_story_bible(
        self,
        project_id,
        db: AsyncSession,
        chapter_number: int | None,
    ) -> ContextPayload:
        statement = select(StoryFact).where(
            StoryFact.project_id == project_id,
            StoryFact.is_active.is_(True),
            StoryFact.superseded_by.is_(None),
            StoryFact.conflict_status != "confirmed",
        )
        if chapter_number is not None:
            statement = statement.where(StoryFact.chapter_number <= chapter_number)
        statement = statement.order_by(StoryFact.chapter_number.asc(), StoryFact.fact_type.asc())
        entries = (await db.scalars(statement)).all()
        if not entries:
            return "", "not_applicable", {"items_count": 0}
        return render_story_bible(entries), "included", {"items_count": len(entries)}

    async def _load_style_reference(
        self,
        project_id,
        db: AsyncSession,
        analysis_id,
        inject_fields: list[str],
    ) -> ContextPayload:
        analysis = await db.scalar(
            select(Analysis).where(
                Analysis.project_id == project_id,
                Analysis.id == analysis_id,
            )
        )
        if analysis is None:
            raise ContextBuilderError(f"style_reference analysis not found: {analysis_id}")
        ensure_style_reference_analysis_type(analysis)
        selected = select_style_reference_fields(analysis.result, inject_fields)
        return (
            render_style_reference(analysis, selected),
            "included",
            {
                "analysis_id": str(analysis.id),
                "analysis_type": analysis.analysis_type,
                "selected_fields": inject_fields,
            },
        )

    async def _get_project_content(
        self,
        db: AsyncSession,
        project_id,
        content_type: str,
    ) -> Content | None:
        return await db.scalar(
            select(Content)
            .options(selectinload(Content.versions))
            .where(Content.project_id == project_id, Content.content_type == content_type)
        )

    def _is_injectable_content(self, content_type: str, content: Content) -> bool:
        if content_type not in APPROVED_CONTENT_TYPES:
            return True
        return content.status == "approved"

    async def _has_approved_content(self, db: AsyncSession, project_id, content_type: str) -> bool:
        content = await self._get_project_content(db, project_id, content_type)
        if content is None or content.status != "approved":
            return False
        return bool(get_current_version_text(content))
