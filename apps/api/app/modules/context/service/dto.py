from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
