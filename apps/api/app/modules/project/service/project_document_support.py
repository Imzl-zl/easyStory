from __future__ import annotations

from collections.abc import Sequence
from typing import Any
import re

from app.modules.content.models import Content

OUTLINE_DOCUMENT_PATH = "大纲/总大纲.md"
OPENING_PLAN_DOCUMENT_PATH = "大纲/开篇设计.md"
CHAPTER_PLAN_DOCUMENT_PATH = "大纲/章节规划.md"
WORLD_SETTING_DOCUMENT_PATH = "设定/世界观.md"
CHARACTER_SETTING_DOCUMENT_PATH = "设定/人物设定.md"
FACTION_SETTING_DOCUMENT_PATH = "设定/势力关系.md"
FORESHADOWING_DOCUMENT_PATH = "设定/伏笔与坑.md"
CHAPTER_DOCUMENT_PATH_PATTERN = re.compile(r"^正文/第(\d{3})章\.md$")

CHAPTER_STATUS_LABELS = {
    "draft": "草稿",
    "approved": "已确认",
    "stale": "待更新",
    "archived": "已归档",
}

CANONICAL_PROJECT_DOCUMENT_PATHS = {
    OUTLINE_DOCUMENT_PATH,
    OPENING_PLAN_DOCUMENT_PATH,
}


def parse_chapter_number_from_document_path(document_path: str) -> int | None:
    matched = CHAPTER_DOCUMENT_PATH_PATTERN.match(document_path)
    if matched is None:
        return None
    return int(matched.group(1))


def is_canonical_project_document_path(document_path: str) -> bool:
    return (
        document_path in CANONICAL_PROJECT_DOCUMENT_PATHS
        or parse_chapter_number_from_document_path(document_path) is not None
    )


def build_setting_document_seed(setting_payload: dict[str, Any] | None, document_path: str) -> str:
    if not isinstance(setting_payload, dict):
        return ""
    if document_path == WORLD_SETTING_DOCUMENT_PATH:
        return _build_world_setting_document(setting_payload)
    if document_path == CHARACTER_SETTING_DOCUMENT_PATH:
        return _build_character_document(setting_payload)
    if document_path == FACTION_SETTING_DOCUMENT_PATH:
        return _build_faction_document(setting_payload)
    if document_path == FORESHADOWING_DOCUMENT_PATH:
        return _build_foreshadowing_document(setting_payload)
    return ""


def build_chapter_plan_document(chapters: Sequence[Content]) -> str:
    if not chapters:
        return ""
    lines = ["# 章节规划", ""]
    for chapter in sorted(chapters, key=lambda item: item.chapter_number or 0):
        chapter_number = chapter.chapter_number or 0
        chapter_label = f"第{chapter_number:03d}章"
        title = chapter.title.strip() if chapter.title else "未命名章节"
        status = CHAPTER_STATUS_LABELS.get(chapter.status, chapter.status)
        lines.append(f"- {chapter_label}：{title}（{status}）")
    return "\n".join(lines).strip()


def _build_world_setting_document(setting_payload: dict[str, Any]) -> str:
    world = _as_dict(setting_payload.get("world_setting"))
    lines: list[str] = ["# 世界观设定", ""]
    _append_field(lines, "题材", setting_payload.get("genre"))
    _append_field(lines, "子题材", setting_payload.get("sub_genre"))
    _append_field(lines, "目标读者", setting_payload.get("target_readers"))
    _append_field(lines, "整体基调", setting_payload.get("tone"))
    _append_field(lines, "世界名称", world.get("name"))
    _append_field(lines, "时代基线", world.get("era_baseline"))
    _append_field(lines, "世界规则", world.get("world_rules"))
    _append_field(lines, "力量体系", world.get("power_system"))
    _append_list_section(lines, "关键地点", world.get("key_locations"))
    return _finalize_seed_document(lines)


def _build_character_document(setting_payload: dict[str, Any]) -> str:
    protagonist = _as_dict(setting_payload.get("protagonist"))
    supporting_roles = _as_list_of_dicts(setting_payload.get("key_supporting_roles"))
    lines: list[str] = ["# 人物设定", ""]
    if protagonist:
        lines.extend(["## 主角", ""])
        _append_character_fields(lines, protagonist)
        lines.append("")
    if supporting_roles:
        lines.extend(["## 重要配角", ""])
        for index, role in enumerate(supporting_roles, start=1):
            lines.append(f"### 配角 {index}")
            lines.append("")
            _append_character_fields(lines, role)
            lines.append("")
    return _finalize_seed_document(lines)


def _build_faction_document(setting_payload: dict[str, Any]) -> str:
    world = _as_dict(setting_payload.get("world_setting"))
    lines: list[str] = ["# 势力关系", ""]
    _append_field(lines, "主线冲突", setting_payload.get("core_conflict"))
    _append_field(lines, "剧情走向", setting_payload.get("plot_direction"))
    _append_list_section(lines, "关键地点 / 势力锚点", world.get("key_locations"))
    return _finalize_seed_document(lines)


def _build_foreshadowing_document(setting_payload: dict[str, Any]) -> str:
    lines: list[str] = ["# 伏笔与坑", ""]
    _append_field(lines, "主线冲突", setting_payload.get("core_conflict"))
    _append_field(lines, "剧情走向", setting_payload.get("plot_direction"))
    _append_field(lines, "特殊要求", setting_payload.get("special_requirements"))
    return _finalize_seed_document(lines)


def _append_character_fields(lines: list[str], payload: dict[str, Any]) -> None:
    _append_field(lines, "姓名", payload.get("name"))
    _append_field(lines, "身份", payload.get("identity"))
    _append_field(lines, "初始处境", payload.get("initial_situation"))
    _append_field(lines, "背景", payload.get("background"))
    _append_field(lines, "性格", payload.get("personality"))
    _append_field(lines, "目标", payload.get("goal"))


def _append_field(lines: list[str], label: str, value: Any) -> None:
    text = _stringify(value)
    if text:
        lines.append(f"- {label}：{text}")


def _append_list_section(lines: list[str], title: str, value: Any) -> None:
    items = [item for item in (_stringify(entry) for entry in _as_list(value)) if item]
    if not items:
        return
    lines.extend([f"## {title}", ""])
    lines.extend([f"- {item}" for item in items])
    lines.append("")


def _finalize_seed_document(lines: list[str]) -> str:
    content_lines = [line for line in lines if line.strip()]
    if len(content_lines) <= 1:
        return ""
    return "\n".join(lines).strip()


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in _as_list(value) if isinstance(item, dict)]


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    return ""
