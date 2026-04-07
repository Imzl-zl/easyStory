from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any, Literal
import uuid

AssistantToolOrigin = Literal["project_document"]
AssistantToolTrustClass = Literal["local_first_party"]
AssistantToolPlane = Literal["resource", "mutation"]
AssistantToolMutability = Literal["read_only", "write"]
AssistantToolExecutionLocus = Literal["local_runtime", "provider_hosted", "remote_mcp"]
AssistantToolApprovalMode = Literal["none", "grant_bound", "always_confirm"]
AssistantToolIdempotencyClass = Literal["safe_read", "conditional_write"]
AssistantToolLifecycleStatus = Literal["reading", "validating", "writing", "committed"]
AssistantToolVisibility = Literal["hidden", "visible"]
AssistantToolHiddenReason = Literal[
    "not_in_project_scope",
    "unsupported_approval_mode",
    "write_grant_unavailable",
]


@dataclass(frozen=True)
class AssistantToolApprovalGrant:
    grant_id: str
    allowed_tool_names: tuple[str, ...]
    target_document_refs: tuple[str, ...]
    binding_version_constraints: dict[str, str]
    base_version_constraints: dict[str, str]
    approval_mode_snapshot: AssistantToolApprovalMode
    buffer_hash_constraints: dict[str, str] = field(default_factory=dict)
    buffer_source_constraints: dict[str, str] = field(default_factory=dict)
    expires_at: str | None = None


@dataclass(frozen=True)
class AssistantToolDescriptor:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    origin: AssistantToolOrigin
    trust_class: AssistantToolTrustClass
    plane: AssistantToolPlane
    mutability: AssistantToolMutability
    execution_locus: AssistantToolExecutionLocus
    approval_mode: AssistantToolApprovalMode
    idempotency_class: AssistantToolIdempotencyClass
    timeout_seconds: int


@dataclass(frozen=True)
class AssistantToolExecutionContext:
    owner_id: uuid.UUID
    project_id: uuid.UUID | None
    arguments: dict[str, Any]
    run_id: uuid.UUID
    run_audit_id: str
    tool_call_id: str
    tool_name: str
    execution_locus: AssistantToolExecutionLocus
    requested_write_scope: str
    allowed_target_document_refs: tuple[str, ...] = ()
    approval_grant: AssistantToolApprovalGrant | None = None
    active_document_ref: str | None = None
    active_binding_version: str | None = None
    active_buffer_state: dict[str, Any] | None = None
    document_context_bindings: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class AssistantToolLifecycleUpdate:
    status: AssistantToolLifecycleStatus
    target_document_refs: tuple[str, ...] = ()
    result_summary: dict[str, Any] | None = None
    result_hash: str | None = None


AssistantToolLifecycleRecorder = Callable[[AssistantToolLifecycleUpdate], None]


@dataclass(frozen=True)
class AssistantToolLoopStateSnapshot:
    pending_tool_calls_snapshot: tuple[dict[str, Any], ...] = ()
    provider_continuation_state: dict[str, Any] | None = None
    normalized_input_items_snapshot: tuple[dict[str, Any], ...] | None = None
    continuation_request_snapshot: dict[str, Any] | None = None
    continuation_compaction_snapshot: dict[str, Any] | None = None
    write_effective: bool = False


AssistantToolLoopStateRecorder = Callable[[AssistantToolLoopStateSnapshot], None]


@dataclass(frozen=True)
class AssistantToolExposureContext:
    project_id: uuid.UUID | None
    requested_write_scope: str
    allowed_target_document_refs: tuple[str, ...] = ()
    active_document_ref: str | None = None
    active_binding_version: str | None = None
    active_buffer_state: dict[str, Any] | None = None
    document_context_bindings: tuple[dict[str, Any], ...] = ()
    tool_catalog_version: str | None = None
    budget_snapshot: dict[str, Any] | None = None
    model_capabilities: dict[str, Any] | None = None
    runtime_supports_approval_resume: bool = False
    run_id: uuid.UUID | None = None


@dataclass(frozen=True)
class AssistantToolPolicyDecision:
    descriptor: AssistantToolDescriptor
    visibility: AssistantToolVisibility
    effective_approval_mode: AssistantToolApprovalMode
    allowed_target_document_refs: tuple[str, ...] = ()
    approval_grant: AssistantToolApprovalGrant | None = None
    hidden_reason: AssistantToolHiddenReason | None = None


@dataclass(frozen=True)
class AssistantToolResultEnvelope:
    tool_call_id: str
    status: Literal["completed", "errored"]
    structured_output: dict[str, Any]
    content_items: list[dict[str, Any]] = field(default_factory=list)
    resource_links: list[dict[str, Any]] = field(default_factory=list)
    error: dict[str, Any] | None = None
    audit: dict[str, Any] | None = None

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)
