from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProjectSettingSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CharacterSetting(ProjectSettingSchema):
    name: str | None = None
    identity: str | None = None
    initial_situation: str | None = None
    background: str | None = None
    personality: str | None = None
    goal: str | None = None


class WorldSetting(ProjectSettingSchema):
    name: str | None = None
    era_baseline: str | None = None
    world_rules: str | None = None
    power_system: str | None = None
    key_locations: list[str] = Field(default_factory=list)


class ScaleSetting(ProjectSettingSchema):
    target_words: int | None = None
    target_chapters: int | None = None
    pacing: str | None = None


class ProjectSetting(ProjectSettingSchema):
    genre: str | None = None
    sub_genre: str | None = None
    target_readers: str | None = None
    tone: str | None = None
    core_conflict: str | None = None
    plot_direction: str | None = None
    protagonist: CharacterSetting | None = None
    key_supporting_roles: list[CharacterSetting] = Field(default_factory=list)
    world_setting: WorldSetting | None = None
    scale: ScaleSetting | None = None
    special_requirements: str | None = None


def merge_project_setting(
    base: ProjectSetting | None,
    patch: ProjectSetting,
) -> ProjectSetting:
    merged = ProjectSetting(
        genre=_merge_optional_scalar(base, patch, "genre"),
        sub_genre=_merge_optional_scalar(base, patch, "sub_genre"),
        target_readers=_merge_optional_scalar(base, patch, "target_readers"),
        tone=_merge_optional_scalar(base, patch, "tone"),
        core_conflict=_merge_optional_scalar(base, patch, "core_conflict"),
        plot_direction=_merge_optional_scalar(base, patch, "plot_direction"),
        protagonist=_merge_character_setting(
            None if base is None else base.protagonist,
            patch.protagonist,
        ),
        key_supporting_roles=_merge_character_setting_list(
            [] if base is None else base.key_supporting_roles,
            patch.key_supporting_roles,
        ),
        world_setting=_merge_world_setting(
            None if base is None else base.world_setting,
            patch.world_setting,
        ),
        scale=_merge_scale_setting(
            None if base is None else base.scale,
            patch.scale,
        ),
        special_requirements=_merge_optional_scalar(base, patch, "special_requirements"),
    )
    return ProjectSetting.model_validate(
        merged.model_dump(mode="json", exclude_none=True)
    )


def extract_project_summary_fields(value: dict[str, Any] | None) -> tuple[str | None, int | None]:
    if value is None:
        return None, None
    scale = value.get("scale") or {}
    return value.get("genre"), scale.get("target_words")


def validate_project_setting(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise TypeError("project_setting must be a JSON object")
    setting = ProjectSetting.model_validate(value)
    return setting.model_dump(mode="json", exclude_none=True)


def _merge_optional_scalar(
    base: ProjectSetting | None,
    patch: ProjectSetting,
    field_name: str,
):
    patch_value = getattr(patch, field_name)
    if patch_value is not None:
        return patch_value
    if base is None:
        return None
    return getattr(base, field_name)


def _merge_non_empty_list(base: list[Any], patch: list[Any]) -> list[Any]:
    return patch if patch else base


def _merge_string_list(base: Sequence[str], patch: Sequence[str]) -> list[str]:
    if not patch:
        return list(base)
    merged: list[str] = []
    seen: set[str] = set()
    for value in [*base, *patch]:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
    return merged


def _merge_character_setting_list(
    base: Sequence[CharacterSetting],
    patch: Sequence[CharacterSetting],
) -> list[CharacterSetting]:
    merged = [item.model_copy(deep=True) for item in base if not _is_character_setting_empty(item)]
    for patch_item in patch:
        if _is_character_setting_empty(patch_item):
            continue
        matched_index = _find_character_setting_merge_index(merged, patch_item)
        if matched_index is None:
            merged.append(patch_item.model_copy(deep=True))
            continue
        merged_item = _merge_character_setting(merged[matched_index], patch_item)
        if merged_item is not None:
            merged[matched_index] = merged_item
    return merged


def _find_character_setting_merge_index(
    items: Sequence[CharacterSetting],
    patch: CharacterSetting,
) -> int | None:
    patch_name = _normalize_optional_text(patch.name)
    if patch_name is not None:
        for index, item in enumerate(items):
            if _normalize_optional_text(item.name) == patch_name:
                return index
    patch_signature = _character_setting_signature(patch)
    if patch_signature is None:
        return None
    for index, item in enumerate(items):
        if _character_setting_signature(item) == patch_signature:
            return index
    return None


def _character_setting_signature(value: CharacterSetting) -> tuple[tuple[str, str], ...] | None:
    signature_items = tuple(
        (field_name, normalized)
        for field_name in (
            "name",
            "identity",
            "initial_situation",
            "background",
            "personality",
            "goal",
        )
        if (normalized := _normalize_optional_text(getattr(value, field_name))) is not None
    )
    return signature_items or None


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _merge_character_setting(
    base: CharacterSetting | None,
    patch: CharacterSetting | None,
) -> CharacterSetting | None:
    if patch is None:
        return base
    merged = CharacterSetting(
        name=patch.name if patch.name is not None else None if base is None else base.name,
        identity=patch.identity if patch.identity is not None else None if base is None else base.identity,
        initial_situation=(
            patch.initial_situation
            if patch.initial_situation is not None
            else None if base is None else base.initial_situation
        ),
        background=(
            patch.background if patch.background is not None else None if base is None else base.background
        ),
        personality=(
            patch.personality
            if patch.personality is not None
            else None if base is None else base.personality
        ),
        goal=patch.goal if patch.goal is not None else None if base is None else base.goal,
    )
    if _is_character_setting_empty(merged):
        return None
    return merged


def _merge_world_setting(
    base: WorldSetting | None,
    patch: WorldSetting | None,
) -> WorldSetting | None:
    if patch is None:
        return base
    merged = WorldSetting(
        name=patch.name if patch.name is not None else None if base is None else base.name,
        era_baseline=(
            patch.era_baseline
            if patch.era_baseline is not None
            else None if base is None else base.era_baseline
        ),
        world_rules=(
            patch.world_rules
            if patch.world_rules is not None
            else None if base is None else base.world_rules
        ),
        power_system=(
            patch.power_system
            if patch.power_system is not None
            else None if base is None else base.power_system
        ),
        key_locations=_merge_string_list(
            [] if base is None else base.key_locations,
            patch.key_locations,
        ),
    )
    if _is_world_setting_empty(merged):
        return None
    return merged


def _merge_scale_setting(
    base: ScaleSetting | None,
    patch: ScaleSetting | None,
) -> ScaleSetting | None:
    if patch is None:
        return base
    merged = ScaleSetting(
        target_words=(
            patch.target_words
            if patch.target_words is not None
            else None if base is None else base.target_words
        ),
        target_chapters=(
            patch.target_chapters
            if patch.target_chapters is not None
            else None if base is None else base.target_chapters
        ),
        pacing=patch.pacing if patch.pacing is not None else None if base is None else base.pacing,
    )
    if _is_scale_setting_empty(merged):
        return None
    return merged


def _is_character_setting_empty(value: CharacterSetting) -> bool:
    return not any(
        (
            value.name,
            value.identity,
            value.initial_situation,
            value.background,
            value.personality,
            value.goal,
        )
    )


def _is_world_setting_empty(value: WorldSetting) -> bool:
    return not any(
        (
            value.name,
            value.era_baseline,
            value.world_rules,
            value.power_system,
            value.key_locations,
        )
    )


def _is_scale_setting_empty(value: ScaleSetting) -> bool:
    return not any(
        (
            value.target_words,
            value.target_chapters,
            value.pacing,
        )
    )
