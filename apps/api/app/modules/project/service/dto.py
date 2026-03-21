from __future__ import annotations

from datetime import datetime
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.project.schemas import ProjectSetting

ProjectStatus = Literal["draft", "active", "completed", "archived"]


class ProjectCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    template_id: uuid.UUID | None = None
    project_setting: ProjectSetting | None = None
    allow_system_credential_pool: bool = False


class ProjectUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    template_id: uuid.UUID | None = None
    allow_system_credential_pool: bool | None = None


class ProjectSummaryDTO(BaseModel):
    id: uuid.UUID
    name: str
    status: ProjectStatus
    genre: str | None
    target_words: int | None
    template_id: uuid.UUID | None
    allow_system_credential_pool: bool
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProjectDetailDTO(ProjectSummaryDTO):
    owner_id: uuid.UUID
    project_setting: ProjectSetting | None


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
    status: ProjectStatus
    project_setting: ProjectSetting | None
