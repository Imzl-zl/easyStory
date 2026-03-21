from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel


class TemplateGuidedQuestionDTO(BaseModel):
    question: str
    variable: str


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
