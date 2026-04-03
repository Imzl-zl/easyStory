from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry.schemas import HookCondition, HookConfig, ModelConfig
from app.shared.runtime.errors import ConfigurationError

ASSISTANT_HOOK_EVENTS = frozenset(
    {"before_assistant_response", "after_assistant_response", "on_error"}
)


@dataclass(frozen=True)
class AssistantHookExecutionContext:
    db: AsyncSession
    event: str
    owner_id: uuid.UUID
    payload: dict[str, Any]
    assistant_agent_id: str | None
    assistant_skill_id: str | None
    assistant_model: ModelConfig
    project_id: uuid.UUID | None

    def read_path(self, path: str) -> Any:
        return read_payload_path(self.payload, path)

    def payload_json(self) -> str:
        return json.dumps(self.payload, ensure_ascii=False, indent=2, sort_keys=True)


def build_assistant_hook_payload(
    *,
    event: str,
    agent_id: str | None,
    skill_id: str | None,
    project_id: uuid.UUID | None,
    messages: list[dict[str, str]],
    input_data: dict[str, Any],
    mcp_servers: list[str],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": event,
        "assistant": {
            "agent_id": agent_id,
            "skill_id": skill_id,
            "project_id": str(project_id) if project_id is not None else None,
            "mcp_servers": list(mcp_servers),
        },
        "conversation": {
            "message_count": len(messages),
            "messages": messages,
        },
        "request": {
            "input_data": input_data,
            "user_input": messages[-1]["content"],
        },
    }
    if extra:
        payload.update(extra)
    return payload


def resolve_assistant_hooks_for_event(
    hooks: list[HookConfig],
    event: str,
) -> list[HookConfig]:
    if event not in ASSISTANT_HOOK_EVENTS:
        raise ConfigurationError(f"Unsupported assistant hook event: {event}")
    matched = [
        hook
        for hook in hooks
        if hook.enabled and hook.trigger.event == event and not hook.trigger.node_types
    ]
    return sorted(matched, key=lambda item: (item.priority, item.id))


def matches_hook_condition(hook: HookConfig, payload: dict[str, Any]) -> bool:
    if hook.condition is None:
        return True
    left = read_payload_path(payload, hook.condition.field)
    return compare_condition(left, hook.condition)


def normalize_hook_result(result: Any) -> Any:
    if result is None or isinstance(result, str | int | float | bool):
        return result
    if isinstance(result, dict | list):
        return result
    return {"type": result.__class__.__name__, "repr": repr(result)}


def serialize_hook_error(exc: Exception) -> dict[str, str]:
    return {"type": exc.__class__.__name__, "message": str(exc)}


def compare_condition(left: Any, condition: HookCondition) -> bool:
    right = condition.value
    if condition.operator == "==":
        return left == right
    if condition.operator == "!=":
        return left != right
    if condition.operator == ">":
        return left > right
    if condition.operator == "<":
        return left < right
    if condition.operator == ">=":
        return left >= right
    if condition.operator == "<=":
        return left <= right
    if condition.operator == "in":
        return _contains(left, right)
    if condition.operator == "not_in":
        return not _contains(left, right)
    raise ConfigurationError(f"Unsupported hook condition operator: {condition.operator}")


def read_payload_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for segment in _normalize_path(path).split("."):
        current = _resolve_segment(current, segment)
    return current


def _contains(left: Any, right: Any) -> bool:
    if isinstance(left, dict):
        return right in left
    if isinstance(left, list | tuple | set | frozenset | str):
        return right in left
    raise ConfigurationError("Hook condition operator 'in' requires a collection value")


def _normalize_path(path: str) -> str:
    normalized = path.strip()
    if not normalized:
        raise ConfigurationError("Hook field path must be a non-empty string")
    return normalized


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
