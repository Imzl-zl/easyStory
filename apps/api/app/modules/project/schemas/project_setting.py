from __future__ import annotations

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
