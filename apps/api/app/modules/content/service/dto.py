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


class StoryAssetSaveDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    content_text: str = Field(min_length=1)
    change_summary: str | None = None
    created_by: ContentCreatedBy = "user"
    change_source: ContentChangeSource = "user_edit"


class StoryAssetDTO(BaseModel):
    project_id: uuid.UUID
    content_id: uuid.UUID
    content_type: AssetType
    title: str
    status: ContentStatus
    version_number: int
    content_text: str


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


class ChapterSummaryDTO(BaseModel):
    project_id: uuid.UUID
    content_id: uuid.UUID
    chapter_number: int
    title: str
    status: ContentStatus
    current_version_number: int
    best_version_number: int | None
    word_count: int | None
    last_edited_at: datetime | None


class ChapterDetailDTO(ChapterSummaryDTO):
    content_text: str
    change_summary: str | None
    created_by: ContentCreatedBy
    change_source: ContentChangeSource
    context_snapshot_hash: str | None


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
