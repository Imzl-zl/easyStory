from __future__ import annotations

from datetime import datetime
import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AnalysisType = Literal["plot", "character", "style", "pacing", "structure"]

EMPTY_PATCH_MESSAGE = "at least one field must be provided"
RESULT_EMPTY_MESSAGE = "result cannot be empty"
RESULT_NULL_MESSAGE = "result cannot be null"
SKILL_KEY_BLANK_MESSAGE = "generated_skill_key cannot be blank"
TRACEABILITY_REQUIRED_MESSAGE = "source_title is required when content_id is omitted"


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_generated_skill_key(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    if value is not None and normalized is None:
        raise ValueError(SKILL_KEY_BLANK_MESSAGE)
    return normalized


def _validate_required_result(value: dict[str, Any]) -> dict[str, Any]:
    if not value:
        raise ValueError(RESULT_EMPTY_MESSAGE)
    return value


def _validate_optional_result(value: dict[str, Any] | None) -> dict[str, Any]:
    if value is None:
        raise ValueError(RESULT_NULL_MESSAGE)
    if not value:
        raise ValueError(RESULT_EMPTY_MESSAGE)
    return value


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
        return _validate_required_result(value)

    @field_validator("source_title", mode="before")
    @classmethod
    def normalize_source_title(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    @field_validator("generated_skill_key", mode="before")
    @classmethod
    def normalize_generated_skill_key(cls, value: str | None) -> str | None:
        return _normalize_generated_skill_key(value)

    @model_validator(mode="after")
    def validate_traceability(self) -> "AnalysisCreateDTO":
        if self.content_id is None and self.source_title is None:
            raise ValueError(TRACEABILITY_REQUIRED_MESSAGE)
        return self


class AnalysisUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_title: str | None = Field(default=None, max_length=255)
    analysis_scope: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    suggestions: dict[str, Any] | None = None
    generated_skill_key: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("source_title", mode="before")
    @classmethod
    def normalize_source_title(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    @field_validator("generated_skill_key", mode="before")
    @classmethod
    def normalize_generated_skill_key(cls, value: str | None) -> str | None:
        return _normalize_generated_skill_key(value)

    @field_validator("result")
    @classmethod
    def validate_result_not_empty(cls, value: dict[str, Any] | None) -> dict[str, Any]:
        return _validate_optional_result(value)

    @model_validator(mode="after")
    def validate_not_empty_patch(self) -> "AnalysisUpdateDTO":
        if not self.model_fields_set:
            raise ValueError(EMPTY_PATCH_MESSAGE)
        return self


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
