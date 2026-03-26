from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry.schemas.config_schemas import HookCondition, HookConfig, NodeConfig, WorkflowConfig
from app.modules.workflow.models import WorkflowExecution
from app.shared.runtime.errors import ConfigurationError

HOOK_EVENT_BUCKETS = {
    "before_node_start": "before",
    "before_generate": "before",
    "before_review": "before",
    "before_fix": "before",
    "after_generate": "after",
    "after_review": "after",
    "on_review_fail": "after",
    "after_fix": "after",
    "after_node_end": "after",
    "on_error": "after",
}


@dataclass(frozen=True)
class HookExecutionContext:
    db: AsyncSession
    workflow: WorkflowExecution
    workflow_config: WorkflowConfig
    node: NodeConfig
    event: str
    owner_id: uuid.UUID
    payload: dict[str, Any]
    node_execution_id: uuid.UUID | None = None

    def read_path(self, path: str) -> Any:
        return read_payload_path(self.payload, path)

    def payload_json(self) -> str:
        return json.dumps(self.payload, ensure_ascii=False, indent=2, sort_keys=True)


def build_hook_payload(
    workflow: WorkflowExecution,
    workflow_config: WorkflowConfig,
    node: NodeConfig,
    event: str,
    *,
    node_execution_id: uuid.UUID | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": event,
        "workflow": {
            "execution_id": str(workflow.id),
            "workflow_id": workflow_config.id,
            "workflow_name": workflow_config.name,
            "project_id": str(workflow.project_id),
        },
        "node": {
            "id": node.id,
            "name": node.name,
            "type": node.node_type,
        },
    }
    if node_execution_id is not None:
        payload["node_execution_id"] = str(node_execution_id)
    if extra:
        payload.update(extra)
    return payload


def resolve_hooks_for_event(
    workflow_snapshot: dict[str, Any],
    node: NodeConfig,
    event: str,
) -> list[HookConfig]:
    bucket = resolve_hook_bucket(event)
    hook_ids = list(node.hooks.get(bucket, []))
    hooks = [load_hook_snapshot(workflow_snapshot, hook_id) for hook_id in hook_ids]
    filtered = [hook for hook in hooks if hook.enabled and _matches_event(hook, node, event)]
    return sorted(filtered, key=lambda item: (item.priority, item.id))


def resolve_hook_bucket(event: str) -> str:
    bucket = HOOK_EVENT_BUCKETS.get(event)
    if bucket is None:
        raise ConfigurationError(f"Unsupported hook event: {event}")
    return bucket


def load_hook_snapshot(workflow_snapshot: dict[str, Any], hook_id: str) -> HookConfig:
    resolved_hooks = workflow_snapshot.get("resolved_hooks")
    if not isinstance(resolved_hooks, dict):
        raise ConfigurationError("Workflow snapshot is missing resolved_hooks")
    raw = resolved_hooks.get(hook_id)
    if not isinstance(raw, dict):
        raise ConfigurationError(f"Hook snapshot not found: {hook_id}")
    return HookConfig.model_validate(raw)


def matches_hook_condition(hook: HookConfig, payload: dict[str, Any]) -> bool:
    if hook.condition is None:
        return True
    left = read_payload_path(payload, hook.condition.field)
    return compare_condition(left, hook.condition)


def compare_condition(left: Any, condition: HookCondition) -> bool:
    right = condition.value
    operator = condition.operator
    if operator == "==":
        return left == right
    if operator == "!=":
        return left != right
    if operator == ">":
        return left > right
    if operator == "<":
        return left < right
    if operator == ">=":
        return left >= right
    if operator == "<=":
        return left <= right
    if operator == "in":
        return _contains(left, right)
    if operator == "not_in":
        return not _contains(left, right)
    raise ConfigurationError(f"Unsupported hook condition operator: {operator}")


def read_payload_path(payload: dict[str, Any], path: str) -> Any:
    normalized = path.strip()
    if not normalized:
        raise ConfigurationError("Hook field path must be a non-empty string")
    current: Any = payload
    for segment in normalized.split("."):
        current = _resolve_segment(current, segment)
    return current


def serialize_hook_error(exc: Exception) -> dict[str, str]:
    return {
        "type": exc.__class__.__name__,
        "message": str(exc),
    }


def normalize_hook_result(result: Any) -> Any:
    if result is None or isinstance(result, str | int | float | bool):
        return result
    if isinstance(result, dict | list):
        return result
    return {"type": result.__class__.__name__, "repr": repr(result)}


def _matches_event(hook: HookConfig, node: NodeConfig, event: str) -> bool:
    if hook.trigger.event != event:
        return False
    if not hook.trigger.node_types:
        return True
    return node.node_type in hook.trigger.node_types


def _contains(left: Any, right: Any) -> bool:
    if isinstance(left, dict):
        return right in left
    if isinstance(left, list | tuple | set | frozenset | str):
        return right in left
    raise ConfigurationError("Hook condition operator 'in' requires a collection value")


def _resolve_segment(current: Any, segment: str) -> Any:
    if isinstance(current, dict):
        if segment not in current:
            raise ConfigurationError(f"Hook payload path not found: {segment}")
        return current[segment]
    if isinstance(current, list):
        return _resolve_list_index(current, segment)
    if hasattr(current, segment):
        return getattr(current, segment)
    raise ConfigurationError(f"Hook payload path not found: {segment}")


def _resolve_list_index(items: list[Any], segment: str) -> Any:
    if not segment.isdigit():
        raise ConfigurationError(f"Hook payload list path must use numeric index: {segment}")
    index = int(segment)
    if index >= len(items):
        raise ConfigurationError(f"Hook payload list index out of range: {segment}")
    return items[index]
