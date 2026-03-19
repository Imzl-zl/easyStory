from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.modules.project.schemas import ProjectSetting


class ProjectSettingUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_setting: ProjectSetting


class SettingCompletenessIssueDTO(BaseModel):
    field: str
    level: Literal["warning", "blocked"]
    message: str


class SettingCompletenessResultDTO(BaseModel):
    status: Literal["ready", "warning", "blocked"]
    issues: list[SettingCompletenessIssueDTO]


class ProjectSettingSnapshotDTO(BaseModel):
    project_id: uuid.UUID
    genre: str | None
    target_words: int | None
    status: str
    project_setting: ProjectSetting | None
