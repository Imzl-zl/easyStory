from __future__ import annotations

from datetime import datetime
import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

AnalysisType = Literal["plot", "character", "style", "pacing", "structure"]


class AnalysisCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_id: uuid.UUID | None = None
    analysis_type: AnalysisType
    source_title: str | None = Field(default=None, max_length=255)
    analysis_scope: dict[str, Any] | None = None
    result: dict[str, Any]
    suggestions: dict[str, Any] | None = None
    generated_skill_key: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("result")
    @classmethod
    def validate_result_not_empty(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("result cannot be empty")
        return value


class AnalysisSummaryDTO(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    content_id: uuid.UUID | None
    analysis_type: AnalysisType
    source_title: str | None
    generated_skill_key: str | None
    created_at: datetime


class AnalysisDetailDTO(AnalysisSummaryDTO):
    analysis_scope: dict[str, Any] | None
    result: dict[str, Any]
    suggestions: dict[str, Any] | None
