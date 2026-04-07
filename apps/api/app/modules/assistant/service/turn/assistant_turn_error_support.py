from __future__ import annotations

from typing import Any
import uuid

from app.shared.runtime.errors import BusinessRuleError

from ..context.assistant_prompt_support import build_document_context_injection_snapshot
from ..hooks_runtime.assistant_hook_support import build_assistant_hook_payload
from .assistant_turn_runtime_support import (
    build_turn_continuation_anchor_snapshot,
    build_turn_run_id,
    dump_turn_messages,
    resolve_requested_write_targets,
)
from ..dto import AssistantTurnRequestDTO, build_turn_messages_digest

ON_ERROR_HOOKS_RUN_MARKER = "_assistant_on_error_hooks_run"


class AssistantDocumentContextProjectionError(BusinessRuleError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class AssistantConversationStateMismatchError(BusinessRuleError):
    code = "conversation_state_mismatch"

    def __init__(self) -> None:
        super().__init__("当前会话状态已变化，请刷新对话后重试。")


class AssistantTurnInProgressError(BusinessRuleError):
    code = "run_in_progress"

    def __init__(self) -> None:
        super().__init__("当前 turn 仍在执行中，请稍后重试。")


def build_request_error_hook_payload(
    *,
    payload: AssistantTurnRequestDTO,
    owner_id: uuid.UUID,
) -> dict[str, Any]:
    document_context = (
        payload.document_context.model_dump(mode="json")
        if payload.document_context is not None
        else None
    )
    return build_assistant_hook_payload(
        event="on_error",
        agent_id=payload.agent_id,
        skill_id=payload.skill_id,
        run_id=build_turn_run_id(
            owner_id=owner_id,
            project_id=payload.project_id,
            conversation_id=payload.conversation_id,
            client_turn_id=payload.client_turn_id,
        ),
        project_id=payload.project_id,
        conversation_id=payload.conversation_id,
        client_turn_id=payload.client_turn_id,
        continuation_anchor=build_turn_continuation_anchor_snapshot(payload),
        messages=dump_turn_messages(payload),
        messages_digest=build_turn_messages_digest(payload.messages),
        document_context=document_context,
        document_context_bindings_snapshot=None,
        document_context_recovery_snapshot=None,
        document_context_injection_snapshot=build_document_context_injection_snapshot(
            document_context
        ),
        compaction_snapshot=None,
        tool_guidance_snapshot=None,
        tool_catalog_version=None,
        exposed_tool_names_snapshot=[],
        requested_write_scope=payload.requested_write_scope,
        requested_write_targets=resolve_requested_write_targets(payload),
        input_data=payload.input_data,
        mcp_servers=[],
    )


def mark_on_error_hooks_run(error: Exception) -> Exception:
    setattr(error, ON_ERROR_HOOKS_RUN_MARKER, True)
    return error


def on_error_hooks_already_run(error: Exception) -> bool:
    return any(
        getattr(candidate, ON_ERROR_HOOKS_RUN_MARKER, False)
        for candidate in iterate_error_candidates(error)
    )


def iterate_error_candidates(error: Exception) -> list[Exception]:
    queue: list[Exception] = [error]
    seen: set[int] = set()
    resolved: list[Exception] = []
    while queue:
        current = queue.pop(0)
        marker = id(current)
        if marker in seen:
            continue
        seen.add(marker)
        resolved.append(current)
        if isinstance(current, BaseExceptionGroup):
            nested = [
                item
                for item in current.exceptions
                if isinstance(item, Exception)
            ]
            queue.extend(nested)
        if isinstance(current.__cause__, Exception):
            queue.append(current.__cause__)
        if isinstance(current.__context__, Exception) and current.__context__ is not current.__cause__:
            queue.append(current.__context__)
    return resolved
