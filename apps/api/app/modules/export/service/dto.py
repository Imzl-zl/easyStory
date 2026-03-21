from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ExportCreateDTO(BaseModel):
    formats: list[str] = Field(default_factory=lambda: ["txt", "markdown"], min_length=1)


class ExportViewDTO(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    format: str
    filename: str
    file_size: int | None
    created_at: datetime
