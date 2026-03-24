from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

VARIABLE_NAMES = {
    "project_setting": "project_setting",
    "outline": "outline",
    "opening_plan": "opening_plan",
    "world_setting": "world_setting",
    "character_profile": "character_profile",
    "chapter_task": "chapter_task",
    "previous_chapters": "previous_content",
    "chapter_summary": "chapter_summary",
    "story_bible": "story_bible",
    "style_reference": "style_reference",
}
VARIABLE_TO_INJECT_TYPE = {value: key for key, value in VARIABLE_NAMES.items()}
AUTO_INJECT_TYPES = frozenset(
    {
        "project_setting",
        "outline",
        "opening_plan",
        "world_setting",
        "character_profile",
        "chapter_task",
        "previous_chapters",
        "chapter_summary",
        "story_bible",
    }
)
SECTION_POLICIES = {
    "project_setting": (1, 0),
    "chapter_task": (1, 0),
    "opening_plan": (2, 200),
    "world_setting": (2, 0),
    "character_profile": (2, 0),
    "story_bible": (2, 500),
    "previous_chapters": (5, 500),
    "chapter_summary": (6, 200),
    "style_reference": (7, 0),
    "outline": (8, 200),
}
STYLE_REFERENCE_MAX_TOKENS = 500
SECTION_TOKEN_CAPS = {
    "style_reference": STYLE_REFERENCE_MAX_TOKENS,
}
OPENING_PLAN_PRIORITY_CHAPTER_LIMIT = 3
OPENING_PLAN_DEGRADED_MAX_CHARS = 400
CHAPTER_SEPARATOR = "\n\n---\n\n"


@dataclass
class ContextSection:
    inject_type: str
    variable_name: str
    content: str
    priority: int
    min_tokens: int
    required: bool
    status: str = "included"
    token_count: int = 0
    original_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_report(self) -> dict[str, Any]:
        report = {
            "type": self.inject_type,
            "variable_name": self.variable_name,
            "status": self.status,
            "required": self.required,
            "token_count": self.token_count,
        }
        if self.original_tokens is not None and self.original_tokens != self.token_count:
            report["original_tokens"] = self.original_tokens
        report.update(self.metadata)
        return report
