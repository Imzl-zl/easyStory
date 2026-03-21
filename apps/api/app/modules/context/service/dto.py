from __future__ import annotations

from datetime import datetime
from enum import Enum
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ContextPreviewRequestDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    chapter_number: int | None = Field(default=None, ge=1)


class ContextPreviewDTO(BaseModel):
    workflow_execution_id: uuid.UUID
    project_id: uuid.UUID
    node_id: str
    node_name: str
    skill_id: str
    model_name: str
    chapter_number: int | None
    referenced_variables: list[str]
    variables: dict[str, str]
    context_report: dict[str, Any]


class StoryFactType(str, Enum):
    CHARACTER_STATE = "character_state"
    LOCATION = "location"
    TIMELINE = "timeline"
    SETTING_CHANGE = "setting_change"
    FORESHADOWING = "foreshadowing"
    RELATIONSHIP = "relationship"


class StoryFactConflictStatus(str, Enum):
    NONE = "none"
    POTENTIAL = "potential"
    CONFIRMED = "confirmed"


class StoryFactCreateResolution(str, Enum):
    AUTO = "auto"
    SUPERSEDE = "supersede"


class StoryFactMutationAction(str, Enum):
    CREATED = "created"
    DUPLICATE = "duplicate"
    POTENTIAL_CONFLICT = "potential_conflict"
    CONFIRMED_CONFLICT = "confirmed_conflict"
    SUPERSEDED = "superseded"


class StoryFactCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chapter_number: int = Field(ge=1)
    source_content_version_id: uuid.UUID
    fact_type: StoryFactType
    subject: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    resolution: StoryFactCreateResolution = StoryFactCreateResolution.AUTO
    supersede_fact_id: uuid.UUID | None = None

    @field_validator("subject", "content")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value cannot be blank")
        return normalized

    @model_validator(mode="after")
    def validate_resolution(self) -> "StoryFactCreateDTO":
        requires_supersede = self.resolution == StoryFactCreateResolution.SUPERSEDE
        if requires_supersede and self.supersede_fact_id is None:
            raise ValueError("supersede_fact_id is required when resolution is supersede")
        if not requires_supersede and self.supersede_fact_id is not None:
            raise ValueError("supersede_fact_id is only allowed when resolution is supersede")
        return self


class StoryFactSupersedeDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    replacement_fact_id: uuid.UUID


class StoryFactDTO(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    chapter_number: int
    source_content_version_id: uuid.UUID
    fact_type: StoryFactType
    subject: str
    content: str
    is_active: bool
    conflict_status: StoryFactConflictStatus
    conflict_with_fact_id: uuid.UUID | None
    superseded_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class StoryFactMutationResultDTO(BaseModel):
    action: StoryFactMutationAction
    fact: StoryFactDTO
    related_fact_ids: list[uuid.UUID] = Field(default_factory=list)
