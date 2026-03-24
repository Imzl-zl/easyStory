from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from .project_setting import CharacterSetting, WorldSetting

PROJECTION_SOURCE = "project_setting"
DIRECT_SETTING_VARIABLE_PATHS = {
    "target_words": "scale.target_words",
}
WORLD_SETTING_FIELDS = (
    ("name", "世界名称"),
    ("era_baseline", "时代基线"),
    ("world_rules", "世界规则"),
    ("power_system", "力量体系"),
)
CHARACTER_FIELDS = (
    ("name", "姓名"),
    ("identity", "身份"),
    ("initial_situation", "初始处境"),
    ("background", "背景"),
    ("personality", "性格"),
    ("goal", "目标"),
)


class ProjectSettingProjectionError(ValueError):
    pass


def build_setting_projection(
    setting_payload: dict[str, Any],
    inject_type: str,
) -> tuple[str, dict[str, Any]]:
    if inject_type == "world_setting":
        return build_world_setting_projection(setting_payload)
    if inject_type == "character_profile":
        return build_character_profile_projection(setting_payload)
    raise ProjectSettingProjectionError(f"Unsupported setting projection: {inject_type}")


def resolve_setting_variable(
    setting_payload: dict[str, Any],
    variable_name: str,
) -> Any:
    _ensure_setting_payload(setting_payload)
    if variable_name == "project_setting":
        return setting_payload
    if variable_name in {"world_setting", "character_profile"}:
        content, _metadata = build_setting_projection(setting_payload, variable_name)
        return content
    path = DIRECT_SETTING_VARIABLE_PATHS.get(variable_name, variable_name)
    return _read_setting_path(setting_payload, path)


def build_world_setting_projection(setting_payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    _ensure_setting_payload(setting_payload)
    world_setting = _parse_world_setting(setting_payload)
    fields = _present_world_setting_fields(world_setting)
    metadata: dict[str, Any] = {
        "projection_source": PROJECTION_SOURCE,
        "fields": fields,
    }
    if world_setting is None or not fields:
        return "", metadata
    if world_setting.key_locations:
        metadata["key_locations_count"] = len(world_setting.key_locations)
    return "\n".join(_world_setting_lines(world_setting)), metadata


def build_character_profile_projection(setting_payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    _ensure_setting_payload(setting_payload)
    protagonist = _parse_character(setting_payload.get("protagonist"), "protagonist")
    supporting_roles = _parse_supporting_roles(setting_payload)
    sections = _character_profile_sections(protagonist, supporting_roles)
    metadata: dict[str, Any] = {
        "projection_source": PROJECTION_SOURCE,
        "has_protagonist": protagonist is not None,
        "supporting_roles_count": len(supporting_roles),
    }
    if not sections:
        return "", metadata
    return "\n\n".join(sections), metadata


def _ensure_setting_payload(setting_payload: dict[str, Any]) -> None:
    if isinstance(setting_payload, dict):
        return
    raise ProjectSettingProjectionError("project_setting projection source is invalid")


def _read_setting_path(setting_payload: dict[str, Any], path: str) -> Any:
    current: Any = setting_payload
    for segment in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
        if current is None:
            return None
    return current


def _parse_world_setting(setting_payload: dict[str, Any]) -> WorldSetting | None:
    raw_world_setting = setting_payload.get("world_setting")
    if raw_world_setting is None:
        return None
    try:
        return WorldSetting.model_validate(raw_world_setting)
    except ValidationError as exc:
        raise ProjectSettingProjectionError("world_setting projection is invalid") from exc


def _parse_character(payload: Any, field_name: str) -> CharacterSetting | None:
    if payload is None:
        return None
    try:
        return CharacterSetting.model_validate(payload)
    except ValidationError as exc:
        raise ProjectSettingProjectionError(f"{field_name} projection is invalid") from exc


def _parse_supporting_roles(setting_payload: dict[str, Any]) -> list[CharacterSetting]:
    raw_roles = setting_payload.get("key_supporting_roles") or []
    if not isinstance(raw_roles, list):
        raise ProjectSettingProjectionError("key_supporting_roles projection is invalid")
    return [_parse_character(item, "key_supporting_roles") for item in raw_roles if item is not None]


def _present_world_setting_fields(world_setting: WorldSetting | None) -> list[str]:
    if world_setting is None:
        return []
    fields = [field_name for field_name, _ in WORLD_SETTING_FIELDS if getattr(world_setting, field_name)]
    if world_setting.key_locations:
        fields.append("key_locations")
    return fields


def _world_setting_lines(world_setting: WorldSetting) -> list[str]:
    lines = [
        f"{label}：{value}"
        for field_name, label in WORLD_SETTING_FIELDS
        if (value := getattr(world_setting, field_name))
    ]
    if world_setting.key_locations:
        lines.append("关键地点：" + "、".join(world_setting.key_locations))
    return lines


def _character_profile_sections(
    protagonist: CharacterSetting | None,
    supporting_roles: list[CharacterSetting],
) -> list[str]:
    sections: list[str] = []
    if protagonist_lines := _character_lines(protagonist):
        sections.append("[主角]\n" + "\n".join(f"- {line}" for line in protagonist_lines))
    if supporting_roles:
        sections.append(_supporting_roles_section(supporting_roles))
    return sections


def _supporting_roles_section(supporting_roles: list[CharacterSetting]) -> str:
    lines: list[str] = []
    for index, role in enumerate(supporting_roles, start=1):
        role_lines = _character_lines(role)
        if not role_lines:
            continue
        title = role.name or role.identity or f"角色{index}"
        lines.append(f"{index}. {title}")
        lines.extend(f"   - {line}" for line in role_lines if line != f"姓名：{title}")
    if not lines:
        return ""
    return "[重要配角]\n" + "\n".join(lines)


def _character_lines(character: CharacterSetting | None) -> list[str]:
    if character is None:
        return []
    return [
        f"{label}：{value}"
        for field_name, label in CHARACTER_FIELDS
        if (value := getattr(character, field_name))
    ]
