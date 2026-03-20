from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

WAITING_CONFIRM_TASK_STATUS = "generating"
TERMINAL_TASK_STATUSES = frozenset({"completed", "skipped"})
VARIABLE_TO_INJECT_TYPE = {
    "project_setting": "project_setting",
    "outline": "outline",
    "opening_plan": "opening_plan",
    "chapter_task": "chapter_task",
    "previous_content": "previous_chapters",
    "story_bible": "story_bible",
}


class ChapterSplitPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chapters: list[dict[str, Any]]


@dataclass(frozen=True)
class NodeOutcome:
    next_node_id: str | None
    pause_reason: str | None = None
    snapshot_extra: dict[str, Any] | None = None
    workflow_status: Literal["failed"] | None = None


@dataclass(frozen=True)
class ReviewCycleOutcome:
    resolution: Literal["passed", "pause", "skip", "fail"]
    final_content: str
    content_source: Literal["generated", "auto_fix"]
    failure_message: str | None = None
