from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChapterTaskDraftDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chapter_number: int
    title: str
    brief: str
    key_characters: list[str] = Field(default_factory=list)
    key_events: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_shape(self) -> "ChapterTaskDraftDTO":
        if self.chapter_number < 1:
            raise ValueError("chapter_number must be >= 1")
        if not self.title.strip():
            raise ValueError("title cannot be empty")
        if not self.brief.strip():
            raise ValueError("brief cannot be empty")
        return self


class ChapterTaskRegenerateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chapters: list[ChapterTaskDraftDTO]

    @model_validator(mode="after")
    def validate_chapters(self) -> "ChapterTaskRegenerateDTO":
        if not self.chapters:
            raise ValueError("chapters cannot be empty")
        numbers = [chapter.chapter_number for chapter in self.chapters]
        if len(numbers) != len(set(numbers)):
            raise ValueError("chapter_number must be unique within chapters")
        return self


class ChapterTaskUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    brief: str | None = None
    key_characters: list[str] | None = None
    key_events: list[str] | None = None

    @model_validator(mode="after")
    def validate_has_updates(self) -> "ChapterTaskUpdateDTO":
        if (
            self.title is None
            and self.brief is None
            and self.key_characters is None
            and self.key_events is None
        ):
            raise ValueError("at least one field must be provided")
        if self.title is not None and not self.title.strip():
            raise ValueError("title cannot be empty")
        if self.brief is not None and not self.brief.strip():
            raise ValueError("brief cannot be empty")
        return self


class ChapterTaskViewDTO(BaseModel):
    task_id: uuid.UUID
    project_id: uuid.UUID
    workflow_execution_id: uuid.UUID
    chapter_number: int
    title: str
    brief: str
    key_characters: list[str]
    key_events: list[str]
    status: str
    content_id: uuid.UUID | None


class ChapterTaskBatchDTO(BaseModel):
    project_id: uuid.UUID
    workflow_execution_id: uuid.UUID
    current_node_id: str | None
    tasks: list[ChapterTaskViewDTO]
