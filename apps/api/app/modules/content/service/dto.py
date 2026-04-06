from __future__ import annotations

from datetime import datetime
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AssetType = Literal["outline", "opening_plan"]
ContentType = Literal["outline", "opening_plan", "chapter"]
ContentStatus = Literal["draft", "approved", "stale", "archived"]
ContentCreatedBy = Literal["system", "user", "ai_assist", "auto_fix", "ai_partial"]
ContentChangeSource = Literal["user_edit", "ai_generate", "ai_fix", "import"]
StoryAssetImpactAction = Literal["mark_stale"]
StoryAssetImpactTarget = Literal["opening_plan", "chapter", "chapter_tasks"]
ChapterImpactAction = Literal["mark_stale"]
ChapterImpactTarget = Literal["chapter"]


class StoryAssetSaveDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    content_text: str = Field(min_length=1)
    change_summary: str | None = None
    created_by: ContentCreatedBy = "user"
    change_source: ContentChangeSource = "user_edit"


class StoryAssetGenerateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str | None = None


class StoryAssetDTO(BaseModel):
    project_id: uuid.UUID
    content_id: uuid.UUID
    content_type: AssetType
    title: str
    status: ContentStatus
    version_number: int
    document_version: str
    content_text: str


class CanonicalProjectDocumentDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: uuid.UUID
    content_id: uuid.UUID
    content_type: ContentType
    title: str = Field(min_length=1)
    chapter_number: int | None = Field(default=None, ge=1)
    content_text: str = ""
    version_number: int | None = Field(default=None, ge=1)
    word_count: int | None = Field(default=None, ge=0)
    updated_at: datetime | None = None


class StoryAssetImpactItemDTO(BaseModel):
    target: StoryAssetImpactTarget
    action: StoryAssetImpactAction
    count: int = Field(ge=1)
    message: str


class StoryAssetImpactSummaryDTO(BaseModel):
    has_impact: bool = False
    total_affected_entries: int = 0
    items: list[StoryAssetImpactItemDTO] = Field(default_factory=list)


class StoryAssetMutationDTO(StoryAssetDTO):
    impact: StoryAssetImpactSummaryDTO = Field(default_factory=StoryAssetImpactSummaryDTO)


class StoryAssetVersionDTO(BaseModel):
    version_number: int
    content_text: str
    created_by: ContentCreatedBy
    change_source: ContentChangeSource
    change_summary: str | None
    word_count: int | None
    is_current: bool
    created_at: datetime


class ChapterSaveDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    content_text: str = Field(min_length=1)
    change_summary: str | None = None
    created_by: ContentCreatedBy = "user"
    change_source: ContentChangeSource = "user_edit"
    context_snapshot_hash: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
    )


class ChapterImpactItemDTO(BaseModel):
    target: ChapterImpactTarget
    action: ChapterImpactAction
    count: int = Field(ge=1)
    message: str


class ChapterImpactSummaryDTO(BaseModel):
    has_impact: bool = False
    total_affected_entries: int = 0
    items: list[ChapterImpactItemDTO] = Field(default_factory=list)


class ChapterSummaryDTO(BaseModel):
    project_id: uuid.UUID
    content_id: uuid.UUID
    chapter_number: int
    title: str
    status: ContentStatus
    current_version_number: int
    document_version: str
    best_version_number: int | None
    word_count: int | None
    last_edited_at: datetime | None


class ChapterDetailDTO(ChapterSummaryDTO):
    content_text: str
    change_summary: str | None
    created_by: ContentCreatedBy
    change_source: ContentChangeSource
    context_snapshot_hash: str | None
    impact: ChapterImpactSummaryDTO = Field(default_factory=ChapterImpactSummaryDTO)


class ChapterVersionDTO(BaseModel):
    version_number: int
    content_text: str
    created_by: ContentCreatedBy
    change_source: ContentChangeSource
    change_summary: str | None
    word_count: int | None
    is_current: bool
    is_best: bool
    context_snapshot_hash: str | None
    created_at: datetime
