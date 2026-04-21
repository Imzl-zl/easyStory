from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any
import json
import re

from app.modules.content.models import Content
from app.shared.runtime.errors import BusinessRuleError

PROJECT_OVERVIEW_DOCUMENT_PATH = "项目说明.md"
OUTLINE_DOCUMENT_PATH = "大纲/总大纲.md"
OPENING_PLAN_DOCUMENT_PATH = "大纲/开篇设计.md"
CHAPTER_PLAN_DOCUMENT_PATH = "大纲/章节规划.md"
WORLD_SETTING_DOCUMENT_PATH = "设定/世界观.md"
CHARACTER_SETTING_DOCUMENT_PATH = "设定/人物.md"
FACTION_SETTING_DOCUMENT_PATH = "设定/势力.md"
FORESHADOWING_DOCUMENT_PATH = "设定/伏笔.md"
SPECIAL_RULES_DOCUMENT_PATH = "设定/特殊规则.md"
DATA_SCHEMA_DOCUMENT_PATH = "数据层/结构定义.json"
CHARACTERS_DATA_DOCUMENT_PATH = "数据层/人物.json"
FACTIONS_DATA_DOCUMENT_PATH = "数据层/势力.json"
CHARACTER_RELATIONS_DATA_DOCUMENT_PATH = "数据层/人物关系.json"
FACTION_RELATIONS_DATA_DOCUMENT_PATH = "数据层/势力关系.json"
MEMBERSHIPS_DATA_DOCUMENT_PATH = "数据层/隶属关系.json"
EVENTS_DATA_DOCUMENT_PATH = "数据层/事件.json"
TURNING_POINTS_DOCUMENT_PATH = "大纲/转折点设计.md"
TIMELINE_INDEX_DOCUMENT_PATH = "时间轴/章节索引.md"
TIMELINE_CHANGE_LOG_DOCUMENT_PATH = "时间轴/状态变更日志.md"
PLACE_NAME_DOCUMENT_PATH = "附录/地名录.md"
ITEMS_DOCUMENT_PATH = "附录/物品功法录.md"
CHRONICLE_DOCUMENT_PATH = "附录/年表.md"
INSPIRATION_DOCUMENT_PATH = "附录/灵感碎片.md"
REJECTED_ARCHIVE_DOCUMENT_PATH = "附录/弃案存档.md"
CONSISTENCY_REPORT_DOCUMENT_PATH = "校验/一致性检查报告.md"
CONFLICT_LOG_DOCUMENT_PATH = "校验/矛盾记录.md"
FORESHADOWING_CHECKLIST_DOCUMENT_PATH = "校验/伏笔回收清单.md"
AI_PROMPT_TEMPLATE_DOCUMENT_PATH = "校验/AI提示词模板.md"
FULL_SETTING_EXPORT_DOCUMENT_PATH = "导出/完整设定集.md"
PROJECT_DOCUMENT_TEMPLATE_VERSION = 3
CHAPTER_DOCUMENT_PATH_PATTERN = re.compile(r"^正文(?:/[^/]+)*/第(\d{3})章\.md$")
SETTING_ROOT_PATH = "设定"
OUTLINE_ROOT_PATH = "大纲"
CONTENT_ROOT_PATH = "正文"
DATA_ROOT_PATH = "数据层"
TIMELINE_ROOT_PATH = "时间轴"
APPENDIX_ROOT_PATH = "附录"
VALIDATION_ROOT_PATH = "校验"
EXPORT_ROOT_PATH = "导出"
FIXED_PROJECT_DOCUMENT_SLOT_ROOTS = {
    SETTING_ROOT_PATH,
    OUTLINE_ROOT_PATH,
    CONTENT_ROOT_PATH,
}
FILE_LAYER_BLOCKED_FILE_ROOT_PATHS = {CONTENT_ROOT_PATH}

LEGACY_DATA_SCHEMA_DOCUMENT_PATH = "数据层/schema.json"
LEGACY_CHARACTERS_DATA_DOCUMENT_PATH = "数据层/characters.json"
LEGACY_FACTIONS_DATA_DOCUMENT_PATH = "数据层/factions.json"
LEGACY_RELATIONS_DATA_DOCUMENT_PATH = "数据层/relations.json"
LEGACY_MEMBERSHIPS_DATA_DOCUMENT_PATH = "数据层/memberships.json"
LEGACY_EVENTS_DATA_DOCUMENT_PATH = "数据层/events.json"

CHAPTER_STATUS_LABELS = {
    "draft": "草稿",
    "approved": "已确认",
    "stale": "待更新",
    "archived": "已归档",
}

SUPPORTED_FILE_SUFFIXES = {".json", ".md"}
CANONICAL_PROJECT_DOCUMENT_PATHS = {
    OUTLINE_DOCUMENT_PATH,
    OPENING_PLAN_DOCUMENT_PATH,
}

DEFAULT_PROJECT_DOCUMENT_FOLDER_PATHS = (
    SETTING_ROOT_PATH,
    OUTLINE_ROOT_PATH,
    CONTENT_ROOT_PATH,
    DATA_ROOT_PATH,
    TIMELINE_ROOT_PATH,
    APPENDIX_ROOT_PATH,
    VALIDATION_ROOT_PATH,
    EXPORT_ROOT_PATH,
)

DEFAULT_PROJECT_DOCUMENT_FILE_PATHS = (
    PROJECT_OVERVIEW_DOCUMENT_PATH,
    WORLD_SETTING_DOCUMENT_PATH,
    CHARACTER_SETTING_DOCUMENT_PATH,
    FACTION_SETTING_DOCUMENT_PATH,
    FORESHADOWING_DOCUMENT_PATH,
    SPECIAL_RULES_DOCUMENT_PATH,
    DATA_SCHEMA_DOCUMENT_PATH,
    CHARACTERS_DATA_DOCUMENT_PATH,
    FACTIONS_DATA_DOCUMENT_PATH,
    CHARACTER_RELATIONS_DATA_DOCUMENT_PATH,
    FACTION_RELATIONS_DATA_DOCUMENT_PATH,
    MEMBERSHIPS_DATA_DOCUMENT_PATH,
    EVENTS_DATA_DOCUMENT_PATH,
    CHAPTER_PLAN_DOCUMENT_PATH,
    TURNING_POINTS_DOCUMENT_PATH,
    TIMELINE_INDEX_DOCUMENT_PATH,
    TIMELINE_CHANGE_LOG_DOCUMENT_PATH,
    PLACE_NAME_DOCUMENT_PATH,
    ITEMS_DOCUMENT_PATH,
    CHRONICLE_DOCUMENT_PATH,
    INSPIRATION_DOCUMENT_PATH,
    REJECTED_ARCHIVE_DOCUMENT_PATH,
    CONSISTENCY_REPORT_DOCUMENT_PATH,
    CONFLICT_LOG_DOCUMENT_PATH,
    FORESHADOWING_CHECKLIST_DOCUMENT_PATH,
    AI_PROMPT_TEMPLATE_DOCUMENT_PATH,
    FULL_SETTING_EXPORT_DOCUMENT_PATH,
)

PROJECT_DOCUMENT_TEMPLATE_V3_FOLDER_PATHS = (
    DATA_ROOT_PATH,
)

PROJECT_DOCUMENT_TEMPLATE_V3_FILE_PATHS = (
    DATA_SCHEMA_DOCUMENT_PATH,
    CHARACTERS_DATA_DOCUMENT_PATH,
    FACTIONS_DATA_DOCUMENT_PATH,
    CHARACTER_RELATIONS_DATA_DOCUMENT_PATH,
    FACTION_RELATIONS_DATA_DOCUMENT_PATH,
    MEMBERSHIPS_DATA_DOCUMENT_PATH,
    EVENTS_DATA_DOCUMENT_PATH,
)


@dataclass(frozen=True)
class ProjectDocumentTemplateFileSeed:
    content: str
    path: str


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


def is_supported_file_project_document_path(document_path: str) -> bool:
    pure_path = _parse_relative_project_document_path(document_path)
    return pure_path is not None and pure_path.suffix.lower() in SUPPORTED_FILE_SUFFIXES


def is_visible_project_document_tree_file_path(document_path: str) -> bool:
    return (
        is_mutable_project_document_file_path(document_path)
        or parse_chapter_number_from_document_path(document_path) is not None
    )


def is_creatable_project_document_file_path(document_path: str) -> bool:
    return (
        is_mutable_project_document_file_path(document_path)
        or parse_chapter_number_from_document_path(document_path) is not None
    )


def is_mutable_project_document_file_path(document_path: str) -> bool:
    pure_path = _parse_relative_project_document_path(document_path)
    return (
        pure_path is not None
        and pure_path.suffix.lower() in SUPPORTED_FILE_SUFFIXES
        and pure_path.parts[0] not in FILE_LAYER_BLOCKED_FILE_ROOT_PATHS
        and not is_canonical_project_document_path(document_path)
    )


def is_mutable_project_document_folder_path(document_path: str) -> bool:
    pure_path = _parse_relative_project_document_path(document_path)
    return (
        pure_path is not None
        and pure_path.suffix.lower() not in SUPPORTED_FILE_SUFFIXES
        and not is_fixed_project_document_folder_path(document_path)
    )


def is_fixed_project_document_folder_path(document_path: str) -> bool:
    pure_path = _parse_relative_project_document_path(document_path)
    return (
        pure_path is not None
        and len(pure_path.parts) == 1
        and pure_path.parts[0] in FIXED_PROJECT_DOCUMENT_SLOT_ROOTS
    )


def list_default_project_document_template_folders() -> tuple[str, ...]:
    return DEFAULT_PROJECT_DOCUMENT_FOLDER_PATHS


def is_default_project_document_template_file_path(document_path: str) -> bool:
    return document_path in DEFAULT_PROJECT_DOCUMENT_FILE_PATHS


def build_default_project_document_template_files(
    *,
    project_name: str,
    project_status: str,
    setting_payload: dict[str, Any] | None,
    chapters: Sequence[Content],
) -> tuple[ProjectDocumentTemplateFileSeed, ...]:
    return build_project_document_template_files(
        project_name=project_name,
        project_status=project_status,
        setting_payload=setting_payload,
        chapters=chapters,
        document_paths=DEFAULT_PROJECT_DOCUMENT_FILE_PATHS,
    )


def build_project_document_template_files(
    *,
    project_name: str,
    project_status: str,
    setting_payload: dict[str, Any] | None,
    chapters: Sequence[Content],
    document_paths: Sequence[str],
) -> tuple[ProjectDocumentTemplateFileSeed, ...]:
    return tuple(
        ProjectDocumentTemplateFileSeed(
            path=document_path,
            content=_build_default_project_document_template_file_content(
                project_name=project_name,
                project_status=project_status,
                setting_payload=setting_payload,
                chapters=chapters,
                document_path=document_path,
            ),
        )
        for document_path in document_paths
    )


def _build_default_project_document_template_file_content(
    *,
    project_name: str,
    project_status: str,
    setting_payload: dict[str, Any] | None,
    chapters: Sequence[Content],
    document_path: str,
) -> str:
    del chapters
    if document_path != PROJECT_OVERVIEW_DOCUMENT_PATH:
        return ""
    return build_project_document_template_seed(
        project_name=project_name,
        project_status=project_status,
        setting_payload=setting_payload,
        document_path=document_path,
    )


def build_project_document_template_seed(
    *,
    project_name: str,
    project_status: str,
    setting_payload: dict[str, Any] | None,
    document_path: str,
    chapter_plan: str = "",
) -> str:
    if document_path == PROJECT_OVERVIEW_DOCUMENT_PATH:
        return _build_project_overview_document(project_name, project_status, setting_payload)
    if document_path == CHAPTER_PLAN_DOCUMENT_PATH:
        return chapter_plan or _build_heading_document("章节规划")
    if document_path == DATA_SCHEMA_DOCUMENT_PATH:
        return _build_data_schema_document()
    if document_path == CHARACTERS_DATA_DOCUMENT_PATH:
        return _build_characters_data_document(setting_payload)
    if document_path == FACTIONS_DATA_DOCUMENT_PATH:
        return _build_empty_json_document("factions")
    if document_path == CHARACTER_RELATIONS_DATA_DOCUMENT_PATH:
        return _build_empty_json_document("character_relations")
    if document_path == FACTION_RELATIONS_DATA_DOCUMENT_PATH:
        return _build_empty_json_document("faction_relations")
    if document_path == MEMBERSHIPS_DATA_DOCUMENT_PATH:
        return _build_empty_json_document("memberships")
    if document_path == EVENTS_DATA_DOCUMENT_PATH:
        return _build_empty_json_document("events")
    setting_document = build_setting_document_seed(setting_payload, document_path)
    if setting_document:
        return setting_document
    if document_path == SPECIAL_RULES_DOCUMENT_PATH:
        return _build_special_rules_document(setting_payload)
    return _build_heading_document(_read_document_title(document_path))


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
        return _build_heading_document("章节规划")
    lines = ["# 章节规划", ""]
    for chapter in sorted(chapters, key=lambda item: item.chapter_number or 0):
        chapter_number = chapter.chapter_number or 0
        chapter_label = f"第{chapter_number:03d}章"
        title = chapter.title.strip() if chapter.title else "未命名章节"
        status = CHAPTER_STATUS_LABELS.get(chapter.status, chapter.status)
        lines.append(f"- {chapter_label}：{title}（{status}）")
    return "\n".join(lines).strip()


def iter_project_document_template_v3_renames() -> tuple[tuple[str, str], ...]:
    return (
        (LEGACY_DATA_SCHEMA_DOCUMENT_PATH, DATA_SCHEMA_DOCUMENT_PATH),
        (LEGACY_CHARACTERS_DATA_DOCUMENT_PATH, CHARACTERS_DATA_DOCUMENT_PATH),
        (LEGACY_FACTIONS_DATA_DOCUMENT_PATH, FACTIONS_DATA_DOCUMENT_PATH),
        (LEGACY_MEMBERSHIPS_DATA_DOCUMENT_PATH, MEMBERSHIPS_DATA_DOCUMENT_PATH),
        (LEGACY_EVENTS_DATA_DOCUMENT_PATH, EVENTS_DATA_DOCUMENT_PATH),
    )


def split_legacy_relations_document(content: str) -> tuple[str, str]:
    trimmed = content.strip()
    if not trimmed:
        return ("", "")
    try:
        parsed = json.loads(trimmed)
    except json.JSONDecodeError as error:
        raise BusinessRuleError(f"旧关系文件不是有效 JSON，无法迁移：{error.msg}") from error
    relations = _read_legacy_relations_collection(parsed)
    character_relations: list[dict[str, Any]] = []
    faction_relations: list[dict[str, Any]] = []
    unsupported_relations: list[dict[str, Any]] = []
    for relation in relations:
        source = _stringify(relation.get("source"))
        target = _stringify(relation.get("target"))
        if source.startswith("char_") and target.startswith("char_"):
            character_relations.append(relation)
            continue
        if source.startswith("fac_") and target.startswith("fac_"):
            faction_relations.append(relation)
            continue
        unsupported_relations.append(relation)
    if unsupported_relations:
        raise BusinessRuleError("旧关系文件包含跨类型关系，无法自动拆分到人物关系或势力关系")
    return (
        _dump_json_collection("character_relations", character_relations),
        _dump_json_collection("faction_relations", faction_relations),
    )


def _parse_relative_project_document_path(document_path: str) -> PurePosixPath | None:
    normalized = document_path.strip()
    if not normalized:
        return None
    pure_path = PurePosixPath(normalized)
    if pure_path.is_absolute() or not pure_path.parts:
        return None
    invalid_parts = {".", "..", ""}
    if any(part in invalid_parts for part in pure_path.parts):
        return None
    return pure_path


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
    lines: list[str] = ["# 人物", ""]
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
    lines: list[str] = ["# 势力", ""]
    _append_field(lines, "主线冲突", setting_payload.get("core_conflict"))
    _append_field(lines, "剧情走向", setting_payload.get("plot_direction"))
    _append_list_section(lines, "关键地点 / 势力锚点", world.get("key_locations"))
    return _finalize_seed_document(lines)


def _build_foreshadowing_document(setting_payload: dict[str, Any]) -> str:
    lines: list[str] = ["# 伏笔", ""]
    _append_field(lines, "主线冲突", setting_payload.get("core_conflict"))
    _append_field(lines, "剧情走向", setting_payload.get("plot_direction"))
    _append_field(lines, "特殊要求", setting_payload.get("special_requirements"))
    return _finalize_seed_document(lines)


def _build_special_rules_document(setting_payload: dict[str, Any] | None) -> str:
    if not isinstance(setting_payload, dict):
        return _build_heading_document("特殊规则")
    world = _as_dict(setting_payload.get("world_setting"))
    lines: list[str] = ["# 特殊规则", ""]
    _append_field(lines, "力量体系", world.get("power_system"))
    _append_field(lines, "世界规则", world.get("world_rules"))
    _append_field(lines, "特殊要求", setting_payload.get("special_requirements"))
    content = _finalize_seed_document(lines)
    return content or _build_heading_document("特殊规则")


def _build_project_overview_document(
    project_name: str,
    project_status: str,
    setting_payload: dict[str, Any] | None,
) -> str:
    scale = _as_dict(setting_payload.get("scale")) if isinstance(setting_payload, dict) else {}
    lines = ["# 项目说明", ""]
    _append_field(lines, "项目名称", project_name)
    _append_field(lines, "当前状态", project_status)
    if isinstance(setting_payload, dict):
        _append_field(lines, "题材", setting_payload.get("genre"))
        _append_field(lines, "核心冲突", setting_payload.get("core_conflict"))
        _append_field(lines, "剧情走向", setting_payload.get("plot_direction"))
    _append_field(lines, "目标字数", scale.get("target_words"))
    _append_field(lines, "目标章节", scale.get("target_chapters"))
    return _finalize_seed_document(lines) or _build_heading_document("项目说明")


def _build_data_schema_document() -> str:
    return """{
  "version": 2,
  "collections": {
    "characters": {
      "path": "人物.json",
      "primary_key": "id"
    },
    "factions": {
      "path": "势力.json",
      "primary_key": "id"
    },
    "character_relations": {
      "path": "人物关系.json",
      "primary_key": "id"
    },
    "faction_relations": {
      "path": "势力关系.json",
      "primary_key": "id"
    },
    "memberships": {
      "path": "隶属关系.json",
      "primary_key": "id"
    },
    "events": {
      "path": "事件.json",
      "primary_key": "id"
    }
  }
}"""


def _build_characters_data_document(setting_payload: dict[str, Any] | None) -> str:
    protagonist = _as_dict(setting_payload.get("protagonist")) if isinstance(setting_payload, dict) else {}
    supporting_roles = (
        _as_list_of_dicts(setting_payload.get("key_supporting_roles"))
        if isinstance(setting_payload, dict)
        else []
    )
    entries: list[str] = []
    if protagonist:
        entries.append(_build_character_data_entry("char_001", protagonist, role="protagonist"))
    for index, role in enumerate(supporting_roles, start=2):
        entries.append(_build_character_data_entry(f"char_{index:03d}", role, role="supporting"))
    body = ",\n".join(entries)
    return "{\n  \"characters\": [\n" + _indent_block(body) + "\n  ]\n}"


def _read_legacy_relations_collection(value: Any) -> list[dict[str, Any]]:
    candidate = value.get("relations") if isinstance(value, dict) else value
    if not isinstance(candidate, list):
        raise BusinessRuleError("旧关系文件必须是数组，或包含 relations 数组的对象")
    if not all(isinstance(item, dict) for item in candidate):
        raise BusinessRuleError("旧关系文件数组中的每一项都必须是对象")
    return [dict(item) for item in candidate]


def _dump_json_collection(collection_name: str, items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    return json.dumps({collection_name: items}, ensure_ascii=False, indent=2)


def _build_character_data_entry(entry_id: str, payload: dict[str, Any], *, role: str) -> str:
    lines = [
        "    {",
        f'      "id": "{entry_id}",',
        f'      "name": {_json_string(payload.get("name"))},',
        f'      "role": "{role}",',
        f'      "identity": {_json_string(payload.get("identity"))},',
        f'      "initial_situation": {_json_string(payload.get("initial_situation"))},',
        f'      "goal": {_json_string(payload.get("goal"))},',
        '      "status": "alive"',
        "    }",
    ]
    return "\n".join(lines)


def _build_empty_json_document(collection_name: str) -> str:
    return "{\n" f'  "{collection_name}": []\n' "}"


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


def _build_heading_document(title: str) -> str:
    return f"# {title}".strip()


def _read_document_title(document_path: str) -> str:
    filename = document_path.split("/")[-1] or document_path
    if filename.endswith(".json"):
        return filename.removesuffix(".json")
    return filename.removesuffix(".md")


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


def _json_string(value: Any) -> str:
    text = _stringify(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _indent_block(content: str) -> str:
    if not content:
        return ""
    return "\n".join(f"  {line}" if line else "" for line in content.splitlines())
