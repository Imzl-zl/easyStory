from __future__ import annotations

from pydantic import Field, model_validator

from app.shared.runtime.llm.llm_protocol import GeminiThinkingLevel, OpenAIReasoningEffort
from app.shared.runtime.llm.llm_reasoning_validation import build_provider_native_reasoning_error

from .base_schema import StrictSchema


class ModelConfig(StrictSchema):
    provider: str | None = None
    name: str | None = None
    required_capabilities: list[str] = Field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 4000
    top_p: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    stop: list[str] | None = None
    reasoning_effort: OpenAIReasoningEffort | None = None
    thinking_level: GeminiThinkingLevel | None = None
    thinking_budget: int | None = Field(default=None, ge=-1)

    @model_validator(mode="after")
    def validate_provider_native_reasoning(self) -> "ModelConfig":
        error = build_provider_native_reasoning_error(
            provider=self.provider,
            reasoning_effort=self.reasoning_effort,
            thinking_level=self.thinking_level,
            thinking_budget=self.thinking_budget,
        )
        if error is not None:
            raise ValueError(error)
        return self


__all__ = [
    "GeminiThinkingLevel",
    "ModelConfig",
    "OpenAIReasoningEffort",
]
