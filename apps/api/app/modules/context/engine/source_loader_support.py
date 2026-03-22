from __future__ import annotations

import json
from typing import Any

from app.modules.analysis.models import Analysis
from app.modules.content.models import Content
from app.modules.context.models import StoryFact

from .errors import ContextBuilderError

DEFAULT_CHAPTER_SUMMARY_COUNT = 5
CHAPTER_SUMMARY_EXCERPT_MAX_CHARS = 120
CHAPTER_SUMMARY_SEPARATOR = "\n\n"
CHAPTER_SUMMARY_ELLIPSIS = "..."
CHAPTER_SUMMARY_MODE = "current_version_excerpt"
STYLE_REFERENCE_ANALYSIS_TYPE = "style"


def dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def get_current_version_text(content: Content) -> str | None:
    versions = sorted(content.versions, key=lambda item: (item.is_current, item.version_number), reverse=True)
    return versions[0].content_text if versions else None


def format_chapter_context(chapters: list[Content]) -> tuple[list[str], list[int]]:
    parts: list[str] = []
    numbers: list[int] = []
    for chapter in chapters:
        text = get_current_version_text(chapter)
        if not text or chapter.chapter_number is None:
            continue
        numbers.append(chapter.chapter_number)
        parts.append(f"第{chapter.chapter_number}章 {chapter.title}\n{text}")
    return parts, numbers


def build_chapter_summaries(chapters: list[Content]) -> tuple[list[str], list[int]]:
    summaries: list[str] = []
    numbers: list[int] = []
    for chapter in chapters:
        summary = _build_chapter_summary_entry(chapter)
        if summary is None or chapter.chapter_number is None:
            continue
        numbers.append(chapter.chapter_number)
        summaries.append(summary)
    return summaries, numbers


def _build_chapter_summary_entry(chapter: Content) -> str | None:
    if chapter.chapter_number is None:
        return None
    text = get_current_version_text(chapter)
    if not text:
        return None
    excerpt = _summarize_chapter_text(text)
    if not excerpt:
        return None
    return f"第{chapter.chapter_number}章 {chapter.title}\n摘要：{excerpt}"


def _summarize_chapter_text(text: str) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= CHAPTER_SUMMARY_EXCERPT_MAX_CHARS:
        return normalized
    truncated = normalized[:CHAPTER_SUMMARY_EXCERPT_MAX_CHARS].rstrip()
    return truncated + CHAPTER_SUMMARY_ELLIPSIS


def render_story_bible(facts: list[StoryFact]) -> str:
    grouped: dict[str, list[str]] = {}
    for fact in facts:
        grouped.setdefault(fact.fact_type, []).append(f"{fact.subject}：{fact.content}")
    lines = []
    for fact_type, items in grouped.items():
        section = f"[{fact_type}]\n" + "\n".join(f"- {item}" for item in items)
        lines.append(section)
    return "\n\n".join(lines)


def select_style_reference_fields(
    result: dict[str, Any],
    inject_fields: list[str],
) -> dict[str, Any]:
    missing_fields = [field_name for field_name in inject_fields if field_name not in result]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ContextBuilderError(f"style_reference fields not found: {missing}")
    return {field_name: result[field_name] for field_name in inject_fields}


def ensure_style_reference_analysis_type(analysis: Analysis) -> None:
    if analysis.analysis_type == STYLE_REFERENCE_ANALYSIS_TYPE:
        return
    raise ContextBuilderError(
        f"style_reference requires style analysis: {analysis.id} ({analysis.analysis_type})"
    )


def render_style_reference(
    analysis: Analysis,
    selected: dict[str, Any],
) -> str:
    lines = []
    if analysis.source_title:
        lines.append(f"来源标题：{analysis.source_title}")
    lines.append(f"分析类型：{analysis.analysis_type}")
    lines.append("风格参考：")
    lines.append(dump_json(selected))
    return "\n".join(lines)
