from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .dto import ProjectDocumentSource

ProjectDocumentContentState = Literal["ready", "empty", "placeholder"]


class ProjectDocumentCatalogEntryDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    document_ref: str = Field(min_length=1)
    resource_uri: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source: ProjectDocumentSource
    document_kind: str = Field(min_length=1)
    mime_type: str = Field(min_length=1)
    schema_id: str | None = None
    content_state: ProjectDocumentContentState
    writable: bool
    version: str = Field(min_length=1)
    updated_at: datetime | None
    catalog_version: str = Field(min_length=1)


class ProjectDocumentReadItemDTO(ProjectDocumentCatalogEntryDTO):
    content: str
    truncated: bool = False
    next_cursor: str | None = None


class ProjectDocumentReadErrorDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ProjectDocumentReadResultDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documents: list[ProjectDocumentReadItemDTO] = Field(default_factory=list)
    errors: list[ProjectDocumentReadErrorDTO] = Field(default_factory=list)
    catalog_version: str = Field(min_length=1)
