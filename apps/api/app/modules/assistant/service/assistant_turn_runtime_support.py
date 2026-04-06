from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from typing import TYPE_CHECKING, Any
import uuid

from app.modules.config_registry.schemas import HookConfig

from .assistant_hook_support import build_assistant_hook_payload
from .assistant_prompt_support import format_project_tool_guidance, require_latest_user_message
from .dto import (
    AssistantHookResultDTO,
    AssistantNormalizedInputItemDTO,
    AssistantOutputItemDTO,
    AssistantOutputMetaDTO,
    AssistantTurnRequestDTO,
    AssistantTurnResponseDTO,
    build_turn_message_records_digest,
    build_turn_messages_digest,
)

if TYPE_CHECKING:
    from .assistant_execution_support import AssistantExecutionSpec
    from .assistant_llm_runtime_support import ResolvedAssistantLlmRuntime
    from .assistant_run_budget import AssistantRunBudget
    from .assistant_tool_runtime_dto import AssistantToolDescriptor, AssistantToolPolicyDecision

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
    compaction_snapshot: dict[str, Any] | None
    document_context: dict[str, Any] | None
    document_context_bindings: list[dict[str, Any]]
    tool_catalog_version: str | None
    requested_write_scope: str
    requested_write_targets: list[str]
    normalized_input_items: list[dict[str, Any]]


@dataclass(frozen=True)
class PreparedAssistantTurn:
    before_payload: dict[str, Any]
    hooks: list[HookConfig]
    project_id: uuid.UUID | None
    prompt: str
    run_budget: "AssistantRunBudget | None"
    resolved_llm_runtime: "ResolvedAssistantLlmRuntime"
    spec: AssistantExecutionSpec
    system_prompt: str | None
    turn_context: AssistantTurnContext
    run_snapshot: "AssistantTurnRunSnapshot"
    tool_policy_decisions: tuple["AssistantToolPolicyDecision", ...]
    visible_tool_descriptors: tuple["AssistantToolDescriptor", ...]


@dataclass(frozen=True)
class AssistantTurnRunSnapshot:
    continuation_anchor_snapshot: dict[str, Any] | None
    compaction_snapshot: dict[str, Any] | None
    document_context_snapshot: dict[str, Any] | None
    document_context_bindings_snapshot: tuple[dict[str, Any], ...]
    tool_catalog_version: str | None
    requested_write_scope: str
    requested_write_targets_snapshot: tuple[str, ...]
    normalized_input_items_snapshot: tuple[dict[str, Any], ...]
    exposed_tool_names_snapshot: tuple[str, ...]
    resolved_tool_descriptor_snapshot: tuple[dict[str, Any], ...]
    tool_policy_decisions_snapshot: tuple[dict[str, Any], ...]
    approval_grants_snapshot: tuple[dict[str, Any], ...]
    budget_snapshot: dict[str, Any] | None
    turn_context_hash: str


def dump_turn_messages(payload: AssistantTurnRequestDTO) -> list[dict[str, str]]:
    return [item.model_dump(mode="json") for item in payload.messages]


def build_completion_messages_digest(
    messages: list[dict[str, str]],
    *,
    assistant_content: str,
) -> str:
    return build_turn_message_records_digest(
        [
            *messages,
            {"role": "assistant", "content": assistant_content},
        ]
    )


def build_turn_context_hash(turn_context: AssistantTurnContext) -> str:
    payload = {
        "continuation_anchor": turn_context.continuation_anchor,
        "compaction_snapshot": turn_context.compaction_snapshot,
        "document_context": turn_context.document_context,
        "document_context_bindings": turn_context.document_context_bindings,
        "messages": turn_context.messages,
        "normalized_input_items": turn_context.normalized_input_items,
        "requested_write_scope": turn_context.requested_write_scope,
        "requested_write_targets": turn_context.requested_write_targets,
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def freeze_turn_run_snapshot(
    turn_context: AssistantTurnContext,
    *,
    tool_policy_decisions: tuple["AssistantToolPolicyDecision", ...],
    budget: "AssistantRunBudget | None" = None,
) -> AssistantTurnRunSnapshot:
    visible_tool_descriptors = tuple(
        item.descriptor
        for item in tool_policy_decisions
        if item.visibility == "visible"
    )
    return AssistantTurnRunSnapshot(
        continuation_anchor_snapshot=deepcopy(turn_context.continuation_anchor),
        compaction_snapshot=deepcopy(turn_context.compaction_snapshot),
        document_context_snapshot=deepcopy(turn_context.document_context),
        document_context_bindings_snapshot=tuple(deepcopy(turn_context.document_context_bindings)),
        tool_catalog_version=turn_context.tool_catalog_version,
        requested_write_scope=turn_context.requested_write_scope,
        requested_write_targets_snapshot=tuple(turn_context.requested_write_targets),
        normalized_input_items_snapshot=tuple(deepcopy(turn_context.normalized_input_items)),
        exposed_tool_names_snapshot=tuple(item.name for item in visible_tool_descriptors),
        resolved_tool_descriptor_snapshot=tuple(
            json.loads(
                json.dumps(item, default=_serialize_tool_descriptor_field, ensure_ascii=False, sort_keys=True)
            )
            for item in visible_tool_descriptors
        ),
        tool_policy_decisions_snapshot=tuple(
            json.loads(
                json.dumps(item, default=_serialize_tool_descriptor_field, ensure_ascii=False, sort_keys=True)
            )
            for item in tool_policy_decisions
        ),
        approval_grants_snapshot=_collect_approval_grants_snapshot(tool_policy_decisions),
        budget_snapshot=None if budget is None else budget.model_dump(),
        turn_context_hash=build_turn_context_hash(turn_context),
    )


def _serialize_tool_descriptor_field(value: Any) -> Any:
    if hasattr(value, "__dict__"):
        return value.__dict__
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _collect_approval_grants_snapshot(
    tool_policy_decisions: tuple["AssistantToolPolicyDecision", ...],
) -> tuple[dict[str, Any], ...]:
    grants_by_id: dict[str, dict[str, Any]] = {}
    for decision in tool_policy_decisions:
        approval_grant = decision.approval_grant
        if approval_grant is None:
            continue
        grants_by_id.setdefault(
            approval_grant.grant_id,
            json.loads(
                json.dumps(
                    approval_grant,
                    default=_serialize_tool_descriptor_field,
                    ensure_ascii=False,
                    sort_keys=True,
                )
            ),
        )
    return tuple(grants_by_id.values())


def build_turn_context(
    spec: AssistantExecutionSpec,
    payload: AssistantTurnRequestDTO,
    *,
    compaction_snapshot: dict[str, Any] | None = None,
    document_context_bindings: list[dict[str, Any]],
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
        compaction_snapshot=deepcopy(compaction_snapshot),
        document_context=(
            payload.document_context.model_dump(mode="json")
            if payload.document_context is not None
            else None
        ),
        document_context_bindings=deepcopy(document_context_bindings),
        tool_catalog_version=(
            payload.document_context.catalog_version
            if payload.document_context is not None
            else None
        ),
        requested_write_scope=payload.requested_write_scope,
        requested_write_targets=resolve_requested_write_targets(payload),
        normalized_input_items=build_normalized_input_items(
            spec,
            payload,
            has_project_scope=project_id is not None,
            compaction_snapshot=compaction_snapshot,
            document_context_bindings=document_context_bindings,
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
    if payload.requested_write_scope != "turn":
        return []
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
    has_project_scope: bool,
    compaction_snapshot: dict[str, Any] | None,
    document_context_bindings: list[dict[str, Any]],
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
    if isinstance(compaction_snapshot, dict):
        items.append(
            AssistantNormalizedInputItemDTO(
                item_type="compacted_context",
                content=_read_compaction_summary(compaction_snapshot),
                payload={
                    key: value
                    for key, value in compaction_snapshot.items()
                    if key != "summary"
                },
            )
        )
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
    project_tool_guidance = format_project_tool_guidance(
        has_project_scope=has_project_scope,
        latest_user_message=require_latest_user_message(payload.messages),
        document_context=(
            payload.document_context.model_dump(mode="json")
            if payload.document_context is not None
            else None
        ),
    )
    if project_tool_guidance:
        items.append(
            AssistantNormalizedInputItemDTO(
                item_type="rule",
                payload={
                    "scope": "project_tool_guidance",
                    "content": project_tool_guidance,
                },
            )
        )
    execution_mode_payload = _build_execution_mode_payload(spec)
    if execution_mode_payload is not None:
        items.append(
            AssistantNormalizedInputItemDTO(
                item_type="skill_instruction",
                payload=execution_mode_payload,
            )
        )
    if payload.hook_ids:
        items.append(
            AssistantNormalizedInputItemDTO(
                item_type="hook_selection",
                payload={"hook_ids": list(payload.hook_ids)},
            )
        )
    items.append(
        AssistantNormalizedInputItemDTO(
            item_type="model_selection",
            payload=spec.model.model_dump(mode="json", exclude_none=True),
        )
    )
    if payload.document_context is not None:
        items.append(
            AssistantNormalizedInputItemDTO(
                item_type="document_context",
                payload=payload.document_context.model_dump(mode="json"),
            )
        )
    items.extend(_build_document_context_binding_items(document_context_bindings))
    return [item.model_dump(mode="json", exclude_none=True) for item in items]


def _build_execution_mode_payload(spec: AssistantExecutionSpec) -> dict[str, Any] | None:
    if spec.agent_id is None and spec.skill_id is None and not spec.mcp_servers:
        return None
    payload: dict[str, Any] = {
        "agent_id": spec.agent_id,
        "skill_id": spec.skill_id,
        "mcp_servers": list(spec.mcp_servers),
    }
    if spec.skill is not None:
        payload["skill_prompt"] = spec.skill.prompt
        payload["skill_prompt_hash"] = _hash_text_content(spec.skill.prompt)
    if spec.system_prompt:
        payload["system_prompt"] = spec.system_prompt
        payload["system_prompt_hash"] = _hash_text_content(spec.system_prompt)
    return payload


def _build_document_context_binding_items(
    document_context_bindings: list[dict[str, Any]],
) -> list[AssistantNormalizedInputItemDTO]:
    return [
        AssistantNormalizedInputItemDTO(
            item_type="document_context_binding",
            payload=binding,
        )
        for binding in document_context_bindings
    ]


def _read_compaction_summary(compaction_snapshot: dict[str, Any]) -> str:
    summary = compaction_snapshot.get("summary")
    if isinstance(summary, str):
        return summary
    return ""


def _hash_text_content(content: str | None) -> str | None:
    if not isinstance(content, str):
        return None
    normalized = content.strip()
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


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
