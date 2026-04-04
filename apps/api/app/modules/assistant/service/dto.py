from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.config_registry.schemas import ModelConfig

ASSISTANT_MAX_MESSAGES = 20
ASSISTANT_MESSAGE_MAX_LENGTH = 8000

AssistantMessageRole = Literal["user", "assistant"]
AssistantRequestedWriteScope = Literal["disabled", "turn"]
AssistantOutputItemType = Literal["text", "tool_call", "tool_result", "reasoning", "refusal"]
AssistantNormalizedInputItemType = Literal[
    "message",
    "rule",
    "skill_instruction",
    "document_context",
    "tool_call",
    "tool_result",
    "reasoning",
    "refusal",
    "compacted_context",
]


class AssistantMessageDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: AssistantMessageRole
    content: str = Field(min_length=1, max_length=ASSISTANT_MESSAGE_MAX_LENGTH)


class AssistantContinuationAnchorDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    previous_run_id: uuid.UUID
    messages_digest: str | None = Field(default=None, min_length=1)


class AssistantActiveBufferStateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dirty: bool
    base_version: str | None = Field(default=None, min_length=1)
    buffer_hash: str | None = Field(default=None, min_length=1)
    source: str | None = Field(default=None, min_length=1)


class AssistantDocumentContextDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_path: str | None = Field(default=None, min_length=1)
    active_document_ref: str | None = Field(default=None, min_length=1)
    active_binding_version: str | None = Field(default=None, min_length=1)
    selected_paths: list[str] = Field(default_factory=list)
    selected_document_refs: list[str] = Field(default_factory=list)
    active_buffer_state: AssistantActiveBufferStateDTO | None = None
    catalog_version: str | None = Field(default=None, min_length=1)


class AssistantNormalizedInputItemDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_type: AssistantNormalizedInputItemType
    role: AssistantMessageRole | None = None
    content: str | None = None
    phase: str | None = None
    payload: Any = None


class AssistantOutputItemDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_type: AssistantOutputItemType
    item_id: str = Field(min_length=1)
    status: str | None = None
    provider_ref: str | None = None
    call_id: str | None = None
    payload: Any = None


class AssistantOutputMetaDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finish_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class AssistantTurnRequestDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: str = Field(min_length=1)
    client_turn_id: str = Field(min_length=1)
    agent_id: str | None = Field(default=None, min_length=1)
    skill_id: str | None = Field(default=None, min_length=1)
    continuation_anchor: AssistantContinuationAnchorDTO | None = None
    stream: bool = True
    hook_ids: list[str] = Field(default_factory=list)
    project_id: uuid.UUID | None = None
    messages: list[AssistantMessageDTO] = Field(min_length=1, max_length=ASSISTANT_MAX_MESSAGES)
    document_context: AssistantDocumentContextDTO | None = None
    requested_write_scope: AssistantRequestedWriteScope = "disabled"
    requested_write_targets: list[str] | None = None
    input_data: dict[str, Any] = Field(default_factory=dict)
    model: ModelConfig | None = None

    @model_validator(mode="after")
    def validate_target(self) -> "AssistantTurnRequestDTO":
        if self.agent_id and self.skill_id:
            raise ValueError("agent_id and skill_id cannot both be provided")
        if self.messages[-1].role != "user":
            raise ValueError("assistant 对话最后一条消息必须是 user")
        if self.continuation_anchor is not None and self.continuation_anchor.messages_digest is not None:
            direct_parent_digest = build_turn_messages_digest(self.messages[:-1])
            if direct_parent_digest != self.continuation_anchor.messages_digest:
                raise ValueError("conversation_state_mismatch")
        if self.requested_write_targets is not None:
            active_document_ref = (
                self.document_context.active_document_ref
                if self.document_context is not None
                else None
            )
            if (
                len(self.requested_write_targets) != 1
                or active_document_ref is None
                or self.requested_write_targets[0] != active_document_ref
            ):
                raise ValueError("unsupported_write_target_scope")
        return self


class AssistantHookResultDTO(BaseModel):
    event: str
    hook_id: str
    action_type: str
    result: Any


class AssistantTurnResponseDTO(BaseModel):
    run_id: uuid.UUID
    conversation_id: str
    client_turn_id: str
    agent_id: str | None
    skill_id: str | None
    provider: str
    model_name: str
    content: str
    output_items: list[AssistantOutputItemDTO] = Field(default_factory=list)
    output_meta: AssistantOutputMetaDTO = Field(default_factory=AssistantOutputMetaDTO)
    hook_results: list[AssistantHookResultDTO] = Field(default_factory=list)
    mcp_servers: list[str] = Field(default_factory=list)
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


def build_turn_messages_digest(messages: list[AssistantMessageDTO]) -> str:
    payload = json.dumps(
        [item.model_dump(mode="json") for item in messages],
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


__all__ = [
    "ASSISTANT_MAX_MESSAGES",
    "ASSISTANT_MESSAGE_MAX_LENGTH",
    "AssistantActiveBufferStateDTO",
    "AssistantContinuationAnchorDTO",
    "AssistantDocumentContextDTO",
    "AssistantHookResultDTO",
    "AssistantMessageDTO",
    "AssistantMessageRole",
    "AssistantNormalizedInputItemDTO",
    "AssistantNormalizedInputItemType",
    "AssistantOutputItemDTO",
    "AssistantOutputItemType",
    "AssistantOutputMetaDTO",
    "AssistantRequestedWriteScope",
    "AssistantTurnRequestDTO",
    "AssistantTurnResponseDTO",
    "build_turn_messages_digest",
]
