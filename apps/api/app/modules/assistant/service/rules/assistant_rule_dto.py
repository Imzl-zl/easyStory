from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AssistantRuleScope = Literal["user", "project"]
ASSISTANT_RULE_CONTENT_MAX_LENGTH = 12000


class AssistantRuleProfileDTO(BaseModel):
    scope: AssistantRuleScope
    enabled: bool
    content: str
    updated_at: datetime | None = None


class AssistantRuleProfileUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    content: str = Field(default="", max_length=ASSISTANT_RULE_CONTENT_MAX_LENGTH)


class AssistantRuleBundleDTO(BaseModel):
    user_content: str | None = None
    project_content: str | None = None
