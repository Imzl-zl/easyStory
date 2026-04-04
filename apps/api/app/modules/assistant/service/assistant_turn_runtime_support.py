from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
import uuid

from app.modules.config_registry.schemas import HookConfig

from .assistant_hook_support import build_assistant_hook_payload
from .assistant_prompt_support import require_latest_user_message
from .dto import (
    AssistantHookResultDTO,
    AssistantNormalizedInputItemDTO,
    AssistantOutputItemDTO,
    AssistantOutputMetaDTO,
    AssistantTurnRequestDTO,
    AssistantTurnResponseDTO,
    build_turn_messages_digest,
)

if TYPE_CHECKING:
    from .assistant_execution_support import AssistantExecutionSpec

ASSISTANT_TURN_RUN_NAMESPACE = uuid.UUID("f3311247-ec4c-5b02-b41b-d4f75220e9f3")


@dataclass(frozen=True)
class AssistantTurnContext:
    run_id: uuid.UUID
    conversation_id: str
    client_turn_id: str
    continuation_anchor: dict[str, Any] | None
    current_user_message: str
    messages: list[dict[str, str]]
    messages_digest: str
    document_context: dict[str, Any] | None
    requested_write_scope: str
    requested_write_targets: list[str]
    normalized_input_items: list[dict[str, Any]]


@dataclass(frozen=True)
class PreparedAssistantTurn:
    before_payload: dict[str, Any]
    hooks: list[HookConfig]
    project_id: uuid.UUID | None
    prompt: str
    spec: AssistantExecutionSpec
    system_prompt: str | None
    turn_context: AssistantTurnContext


def dump_turn_messages(payload: AssistantTurnRequestDTO) -> list[dict[str, str]]:
    return [item.model_dump(mode="json") for item in payload.messages]


def build_turn_context(
    spec: AssistantExecutionSpec,
    payload: AssistantTurnRequestDTO,
    *,
    owner_id: uuid.UUID,
    project_id: uuid.UUID | None,
    user_rule_content: str | None,
    project_rule_content: str | None,
) -> AssistantTurnContext:
    return AssistantTurnContext(
        run_id=build_turn_run_id(
            owner_id=owner_id,
            project_id=project_id,
            conversation_id=payload.conversation_id,
            client_turn_id=payload.client_turn_id,
        ),
        conversation_id=payload.conversation_id,
        client_turn_id=payload.client_turn_id,
        continuation_anchor=(
            payload.continuation_anchor.model_dump(mode="json")
            if payload.continuation_anchor is not None
            else None
        ),
        current_user_message=require_latest_user_message(payload.messages),
        messages=dump_turn_messages(payload),
        messages_digest=build_turn_messages_digest(payload.messages),
        document_context=(
            payload.document_context.model_dump(mode="json")
            if payload.document_context is not None
            else None
        ),
        requested_write_scope=payload.requested_write_scope,
        requested_write_targets=resolve_requested_write_targets(payload),
        normalized_input_items=build_normalized_input_items(
            spec,
            payload,
            user_rule_content=user_rule_content,
            project_rule_content=project_rule_content,
        ),
    )


def build_before_assistant_payload(
    spec: AssistantExecutionSpec,
    payload: AssistantTurnRequestDTO,
    project_id: uuid.UUID | None,
    turn_context: AssistantTurnContext,
) -> dict[str, Any]:
    return build_assistant_hook_payload(
        event="before_assistant_response",
        agent_id=spec.agent_id,
        skill_id=spec.skill_id,
        run_id=turn_context.run_id,
        project_id=project_id,
        conversation_id=turn_context.conversation_id,
        client_turn_id=turn_context.client_turn_id,
        continuation_anchor=turn_context.continuation_anchor,
        messages=turn_context.messages,
        messages_digest=turn_context.messages_digest,
        document_context=turn_context.document_context,
        requested_write_scope=turn_context.requested_write_scope,
        requested_write_targets=turn_context.requested_write_targets,
        input_data=payload.input_data,
        mcp_servers=spec.mcp_servers,
    )


def build_after_assistant_payload(
    spec: AssistantExecutionSpec,
    payload: AssistantTurnRequestDTO,
    project_id: uuid.UUID | None,
    turn_context: AssistantTurnContext,
    content: str,
) -> dict[str, Any]:
    return build_assistant_hook_payload(
        event="after_assistant_response",
        agent_id=spec.agent_id,
        skill_id=spec.skill_id,
        run_id=turn_context.run_id,
        project_id=project_id,
        conversation_id=turn_context.conversation_id,
        client_turn_id=turn_context.client_turn_id,
        continuation_anchor=turn_context.continuation_anchor,
        messages=turn_context.messages,
        messages_digest=turn_context.messages_digest,
        document_context=turn_context.document_context,
        requested_write_scope=turn_context.requested_write_scope,
        requested_write_targets=turn_context.requested_write_targets,
        input_data=payload.input_data,
        mcp_servers=spec.mcp_servers,
        extra={"response": {"content": content}},
    )


def build_turn_response(
    spec: AssistantExecutionSpec,
    raw_output: dict[str, Any],
    content: str,
    hook_results: list[AssistantHookResultDTO],
    turn_context: AssistantTurnContext,
) -> AssistantTurnResponseDTO:
    return AssistantTurnResponseDTO(
        run_id=turn_context.run_id,
        conversation_id=turn_context.conversation_id,
        client_turn_id=turn_context.client_turn_id,
        agent_id=spec.agent_id,
        skill_id=spec.skill_id,
        provider=spec.model.provider or "",
        model_name=raw_output.get("model_name") or spec.model.name or "",
        content=content,
        output_items=build_output_items(turn_context, raw_output, content),
        output_meta=build_output_meta(raw_output),
        hook_results=hook_results,
        mcp_servers=spec.mcp_servers,
        input_tokens=raw_output.get("input_tokens"),
        output_tokens=raw_output.get("output_tokens"),
        total_tokens=raw_output.get("total_tokens"),
    )


def build_turn_run_id(
    *,
    owner_id: uuid.UUID,
    project_id: uuid.UUID | None,
    conversation_id: str,
    client_turn_id: str,
) -> uuid.UUID:
    turn_scope = ":".join(
        [
            str(owner_id),
            str(project_id) if project_id is not None else "none",
            conversation_id,
            client_turn_id,
        ]
    )
    return uuid.uuid5(ASSISTANT_TURN_RUN_NAMESPACE, turn_scope)


def resolve_requested_write_targets(payload: AssistantTurnRequestDTO) -> list[str]:
    if payload.requested_write_targets is not None:
        return list(payload.requested_write_targets)
    active_document_ref = payload.document_context.active_document_ref if payload.document_context else None
    if active_document_ref is None:
        return []
    return [active_document_ref]


def build_normalized_input_items(
    spec: AssistantExecutionSpec,
    payload: AssistantTurnRequestDTO,
    *,
    user_rule_content: str | None,
    project_rule_content: str | None,
) -> list[dict[str, Any]]:
    items: list[AssistantNormalizedInputItemDTO] = [
        AssistantNormalizedInputItemDTO(
            item_type="message",
            role=message.role,
            content=message.content,
        )
        for message in payload.messages
    ]
    if user_rule_content:
        items.append(
            AssistantNormalizedInputItemDTO(
                item_type="rule",
                payload={"scope": "user", "content": user_rule_content},
            )
        )
    if project_rule_content:
        items.append(
            AssistantNormalizedInputItemDTO(
                item_type="rule",
                payload={"scope": "project", "content": project_rule_content},
            )
        )
    if spec.agent_id is not None or spec.skill_id is not None:
        items.append(
            AssistantNormalizedInputItemDTO(
                item_type="skill_instruction",
                payload={"agent_id": spec.agent_id, "skill_id": spec.skill_id},
            )
        )
    if payload.document_context is not None:
        items.append(
            AssistantNormalizedInputItemDTO(
                item_type="document_context",
                payload=payload.document_context.model_dump(mode="json"),
            )
        )
    return [item.model_dump(mode="json", exclude_none=True) for item in items]


def build_output_items(
    turn_context: AssistantTurnContext,
    raw_output: dict[str, Any],
    content: str,
) -> list[AssistantOutputItemDTO]:
    existing_items = raw_output.get("output_items")
    if isinstance(existing_items, list):
        return [AssistantOutputItemDTO.model_validate(item) for item in existing_items]
    provider_ref = raw_output.get("provider")
    if provider_ref is not None and not isinstance(provider_ref, str):
        provider_ref = str(provider_ref)
    return [
        AssistantOutputItemDTO(
            item_type="text",
            item_id=f"{turn_context.run_id}:text:0",
            status="completed",
            provider_ref=provider_ref,
            payload={"content": content, "phase": "final"},
        )
    ]


def build_output_meta(raw_output: dict[str, Any]) -> AssistantOutputMetaDTO:
    return AssistantOutputMetaDTO(
        finish_reason=_read_optional_output_string(raw_output, "finish_reason"),
        input_tokens=raw_output.get("input_tokens"),
        output_tokens=raw_output.get("output_tokens"),
        total_tokens=raw_output.get("total_tokens"),
    )


def _read_optional_output_string(raw_output: dict[str, Any], field: str) -> str | None:
    value = raw_output.get(field)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
