from __future__ import annotations

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
    tool_call_id: str
    tool_name: str
    execution_locus: AssistantToolExecutionLocus


@dataclass(frozen=True)
class AssistantToolExposureContext:
    project_id: uuid.UUID | None
    requested_write_scope: str
    tool_catalog_version: str | None = None
    budget_snapshot: dict[str, Any] | None = None
    model_capabilities: dict[str, Any] | None = None
    runtime_supports_approval_resume: bool = False


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
