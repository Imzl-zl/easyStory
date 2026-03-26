from __future__ import annotations

import uuid

from app.shared.runtime.errors import ModelFallbackExhaustedError

from .workflow_runtime_llm_support import MODEL_FALLBACK_PAUSE_REASON
from .workflow_runtime_shared import NodeOutcome, ReviewCycleOutcome


def resolve_review_pause_reason(review_outcome: ReviewCycleOutcome) -> str:
    if review_outcome.pause_reason is not None:
        return review_outcome.pause_reason
    return "review_failed"


def build_failure_snapshot(
    *,
    execution_id: uuid.UUID,
    chapter_number: int,
    content_id: uuid.UUID | None,
) -> dict[str, str | int | None]:
    return {
        "current_node_execution_id": str(execution_id),
        "current_chapter_number": chapter_number,
        "content_id": str(content_id) if content_id is not None else None,
    }


def build_model_fallback_node_outcome(
    exc: ModelFallbackExhaustedError,
    *,
    execution_id: uuid.UUID,
    next_node_id: str,
    chapter_number: int | None = None,
    content_id: uuid.UUID | None = None,
    hook_payload: dict[str, object] | None = None,
) -> NodeOutcome:
    snapshot: dict[str, object] = {
        "current_node_execution_id": str(execution_id),
        "pending_actions": [{"type": "model_fallback_exhausted", "detail": exc.message}],
    }
    if chapter_number is not None:
        snapshot["current_chapter_number"] = chapter_number
    if content_id is not None:
        snapshot["content_id"] = str(content_id)
    if exc.action == "pause":
        return NodeOutcome(
            next_node_id=next_node_id,
            pause_reason=MODEL_FALLBACK_PAUSE_REASON,
            snapshot_extra=snapshot,
            node_execution_id=execution_id,
            hook_payload=hook_payload,
        )
    return NodeOutcome(
        next_node_id=next_node_id,
        snapshot_extra=snapshot,
        workflow_status="failed",
        node_execution_id=execution_id,
        hook_payload=hook_payload,
    )
