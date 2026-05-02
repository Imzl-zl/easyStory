from __future__ import annotations

import hashlib
import json

from app.modules.project.service.project_document_buffer_state_support import (
    extract_trusted_project_document_buffer_snapshot,
)

from .assistant_tool_runtime_dto import (
    AssistantToolApprovalGrant,
    AssistantToolDescriptor,
    AssistantToolExposureContext,
    AssistantToolPolicyDecision,
)

PROJECT_DOCUMENT_WRITE_TOOL_NAMES = ("project.write_document", "project.edit_document")


class AssistantToolPolicyResolver:
    def resolve(
        self,
        *,
        descriptor: AssistantToolDescriptor,
        context: AssistantToolExposureContext,
    ) -> AssistantToolPolicyDecision:
        if descriptor.origin == "project_document" and context.project_id is None:
            return _build_hidden_decision(
                descriptor,
                reason="not_in_project_scope",
            )
        # v1A still has no formal approval_request / approval_grant / resume protocol,
        # so always_confirm descriptors must remain hidden regardless of runtime flags.
        if descriptor.approval_mode == "always_confirm":
            return _build_hidden_decision(
                descriptor,
                reason="unsupported_approval_mode",
            )
        if descriptor.approval_mode != "grant_bound":
            return _build_visible_decision(descriptor)
        if not _has_grant_bound_write_access(context):
            return _build_hidden_decision(
                descriptor,
                reason="write_grant_unavailable",
            )
        return _build_visible_decision(
            descriptor,
            allowed_target_document_refs=context.allowed_target_document_refs,
            approval_grant=_build_turn_approval_grant(
                descriptor=descriptor,
                context=context,
            ),
        )


def _build_visible_decision(
    descriptor: AssistantToolDescriptor,
    *,
    allowed_target_document_refs: tuple[str, ...] = (),
    approval_grant: AssistantToolApprovalGrant | None = None,
) -> AssistantToolPolicyDecision:
    return AssistantToolPolicyDecision(
        descriptor=descriptor,
        visibility="visible",
        effective_approval_mode=descriptor.approval_mode,
        allowed_target_document_refs=allowed_target_document_refs,
        approval_grant=approval_grant,
    )


def _build_hidden_decision(
    descriptor: AssistantToolDescriptor,
    *,
    reason: str,
) -> AssistantToolPolicyDecision:
    return AssistantToolPolicyDecision(
        descriptor=descriptor,
        visibility="hidden",
        effective_approval_mode=descriptor.approval_mode,
        hidden_reason=reason,
    )


def _has_grant_bound_write_access(context: AssistantToolExposureContext) -> bool:
    if context.requested_write_scope != "turn":
        return False
    if len(context.allowed_target_document_refs) != 1:
        return False
    if context.active_document_ref is None:
        return False
    if context.allowed_target_document_refs[0] != context.active_document_ref:
        return False
    if context.active_binding_version is None:
        return False
    if not _has_writable_active_binding(context):
        return False
    return extract_trusted_project_document_buffer_snapshot(context.active_buffer_state) is not None


def _has_writable_active_binding(context: AssistantToolExposureContext) -> bool:
    for item in context.document_context_bindings:
        if not isinstance(item, dict):
            continue
        if item.get("selection_role") != "active":
            continue
        if item.get("document_ref") != context.active_document_ref:
            continue
        return item.get("writable") is True
    return False


def _build_turn_approval_grant(
    *,
    descriptor: AssistantToolDescriptor,
    context: AssistantToolExposureContext,
) -> AssistantToolApprovalGrant:
    target_document_ref = context.allowed_target_document_refs[0]
    binding_version = str(context.active_binding_version)
    trusted_snapshot = extract_trusted_project_document_buffer_snapshot(
        context.active_buffer_state
    )
    if trusted_snapshot is None:
        raise RuntimeError("grant_bound write access requires trusted active_buffer_state")
    allowed_tool_names = _resolve_grant_allowed_tool_names(descriptor)
    grant_id = _build_turn_approval_grant_id(
        allowed_tool_names=allowed_tool_names,
        context=context,
        target_document_ref=target_document_ref,
        binding_version=binding_version,
        base_version=trusted_snapshot.base_version,
        buffer_hash=trusted_snapshot.buffer_hash,
        buffer_source=trusted_snapshot.source,
    )
    return AssistantToolApprovalGrant(
        grant_id=grant_id,
        allowed_tool_names=allowed_tool_names,
        target_document_refs=(target_document_ref,),
        binding_version_constraints={target_document_ref: binding_version},
        base_version_constraints={target_document_ref: trusted_snapshot.base_version},
        approval_mode_snapshot=descriptor.approval_mode,
        buffer_hash_constraints={target_document_ref: trusted_snapshot.buffer_hash},
        buffer_source_constraints={target_document_ref: trusted_snapshot.source},
        expires_at=None,
    )


def _resolve_grant_allowed_tool_names(descriptor: AssistantToolDescriptor) -> tuple[str, ...]:
    if descriptor.name in PROJECT_DOCUMENT_WRITE_TOOL_NAMES:
        return PROJECT_DOCUMENT_WRITE_TOOL_NAMES
    return (descriptor.name,)


def _build_turn_approval_grant_id(
    *,
    allowed_tool_names: tuple[str, ...],
    context: AssistantToolExposureContext,
    target_document_ref: str,
    binding_version: str,
    base_version: str,
    buffer_hash: str,
    buffer_source: str,
) -> str:
    payload = {
        "active_document_ref": context.active_document_ref,
        "base_version": base_version,
        "buffer_hash": buffer_hash,
        "buffer_source": buffer_source,
        "binding_version": binding_version,
        "allowed_tool_names": allowed_tool_names,
        "project_id": str(context.project_id) if context.project_id is not None else None,
        "requested_write_scope": context.requested_write_scope,
        "run_id": str(context.run_id) if context.run_id is not None else None,
        "target_document_ref": target_document_ref,
    }
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"grant:{digest}"
