from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AssetType = Literal["outline", "opening_plan"]


class StoryAssetSaveDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    content_text: str = Field(min_length=1)
    change_summary: str | None = None
    created_by: str = "user"
    change_source: str = "user_edit"


class StoryAssetDTO(BaseModel):
    project_id: uuid.UUID
    content_id: uuid.UUID
    content_type: AssetType
    title: str
    status: str
    version_number: int
    content_text: str
