from __future__ import annotations

from datetime import datetime
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.workflow.service.dto import WorkflowExecutionSummaryDTO
from app.modules.project.schemas import ProjectSetting

ProjectStatus = Literal["draft", "active", "completed", "archived"]
SettingImpactAction = Literal["mark_stale"]
SettingImpactTarget = Literal["outline", "opening_plan", "chapter", "chapter_tasks"]
PreparationAssetStepStatus = Literal["not_started", "draft", "approved", "stale", "archived"]
PreparationChapterTaskStepStatus = Literal[
    "not_started",
    "pending",
    "generating",
    "completed",
    "failed",
    "stale",
    "interrupted",
]
PreparationNextStep = Literal["setting", "outline", "opening_plan", "chapter_tasks", "workflow", "chapter"]


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


class ProjectSettingImpactItemDTO(BaseModel):
    target: SettingImpactTarget
    action: SettingImpactAction
    count: int = Field(ge=1)
    message: str


class ProjectSettingImpactSummaryDTO(BaseModel):
    has_impact: bool = False
    total_affected_entries: int = 0
    items: list[ProjectSettingImpactItemDTO] = Field(default_factory=list)


class ProjectSettingSnapshotDTO(BaseModel):
    project_id: uuid.UUID
    genre: str | None
    target_words: int | None
    status: ProjectStatus
    project_setting: ProjectSetting | None
    impact: ProjectSettingImpactSummaryDTO = Field(default_factory=ProjectSettingImpactSummaryDTO)


class PreparationAssetStatusDTO(BaseModel):
    content_id: uuid.UUID | None
    step_status: PreparationAssetStepStatus
    content_status: Literal["draft", "approved", "stale", "archived"] | None
    version_number: int | None
    has_content: bool
    updated_at: datetime | None


class PreparationChapterTaskCountsDTO(BaseModel):
    pending: int = 0
    generating: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    stale: int = 0
    interrupted: int = 0


class PreparationChapterTaskStatusDTO(BaseModel):
    workflow_execution_id: uuid.UUID | None
    step_status: PreparationChapterTaskStepStatus
    total: int
    counts: PreparationChapterTaskCountsDTO


class ProjectPreparationStatusDTO(BaseModel):
    project_id: uuid.UUID
    setting: SettingCompletenessResultDTO
    outline: PreparationAssetStatusDTO
    opening_plan: PreparationAssetStatusDTO
    chapter_tasks: PreparationChapterTaskStatusDTO
    active_workflow: WorkflowExecutionSummaryDTO | None
    can_start_workflow: bool
    next_step: PreparationNextStep
    next_step_detail: str
