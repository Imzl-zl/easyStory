from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .guided_question_support import (
    normalize_guided_question_text,
    normalize_guided_question_variable,
)


class TemplateGuidedQuestionDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    variable: str

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        return normalize_guided_question_text(value, field_name="question")

    @field_validator("variable")
    @classmethod
    def validate_variable(cls, value: str) -> str:
        return normalize_guided_question_variable(value)


class TemplateCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    genre: str | None = None
    workflow_id: str
    guided_questions: list[TemplateGuidedQuestionDTO] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_shape(self) -> "TemplateCreateDTO":
        if not self.name.strip():
            raise ValueError("name cannot be empty")
        if not self.workflow_id.strip():
            raise ValueError("workflow_id cannot be empty")
        variables = [question.variable for question in self.guided_questions]
        if len(variables) != len(set(variables)):
            raise ValueError("guided question variables must be unique")
        return self


class TemplateUpdateDTO(TemplateCreateDTO):
    pass


class TemplateNodeViewDTO(BaseModel):
    id: uuid.UUID
    node_order: int
    node_id: str | None
    node_name: str | None
    node_type: str
    skill_id: str | None
    config: dict[str, Any] | None
    position_x: int | None
    position_y: int | None
    ui_config: dict[str, Any] | None


class TemplateSummaryDTO(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    genre: str | None
    workflow_id: str | None
    is_builtin: bool
    node_count: int
    created_at: datetime
    updated_at: datetime


class TemplateDetailDTO(TemplateSummaryDTO):
    config: dict[str, Any] | None
    guided_questions: list[TemplateGuidedQuestionDTO]
    nodes: list[TemplateNodeViewDTO]
