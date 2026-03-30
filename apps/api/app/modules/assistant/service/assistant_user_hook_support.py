from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import re
import secrets

from pydantic import ValidationError
import yaml

from app.modules.config_registry.schemas import HookConfig
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError

from .assistant_hook_dto import (
    AssistantAgentHookActionDTO,
    AssistantHookActionDTO,
    AssistantHookCreateDTO,
    AssistantHookDetailDTO,
    AssistantHookEvent,
    AssistantHookSummaryDTO,
    AssistantHookUpdateDTO,
    AssistantMcpHookActionDTO,
    normalize_assistant_hook_name,
)
from .preferences_support import normalize_optional_text

HOOK_FILE_NAME = "HOOK.yaml"
HOOKS_DIR_NAME = "hooks"
USER_HOOK_AUTHOR = "user"
USER_HOOK_ID_PREFIX = "hook.user."
HOOK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
YAML_ROOT_KEY_HOOK = "hook"
DEFAULT_HOOK_PRIORITY = 10
DEFAULT_HOOK_TIMEOUT = 30


@dataclass(frozen=True)
class StoredAssistantHook:
    id: str
    name: str
    description: str | None
    enabled: bool
    event: AssistantHookEvent
    action: AssistantHookActionDTO
    updated_at: datetime | None
    path: Path


def build_hook_summary(record: StoredAssistantHook) -> AssistantHookSummaryDTO:
    return AssistantHookSummaryDTO(
        id=record.id,
        file_name=record.path.name,
        name=record.name,
        description=record.description,
        enabled=record.enabled,
        event=record.event,
        action=_copy_hook_action(record.action),
        updated_at=record.updated_at,
    )


def build_hook_detail(record: StoredAssistantHook) -> AssistantHookDetailDTO:
    return AssistantHookDetailDTO(**build_hook_summary(record).model_dump())


def build_runtime_hook(record: StoredAssistantHook) -> HookConfig:
    return HookConfig.model_validate(
        {
            "id": record.id,
            "name": record.name,
            "description": record.description,
            "author": USER_HOOK_AUTHOR,
            "enabled": record.enabled,
            "trigger": {"event": record.event, "node_types": []},
            "action": {
                "type": record.action.action_type,
                "config": _build_hook_action_config(record.action),
            },
            "priority": DEFAULT_HOOK_PRIORITY,
            "timeout": DEFAULT_HOOK_TIMEOUT,
        }
    )


def build_hook_path(root: Path, user_id, hook_id: str) -> Path:
    validate_hook_id(hook_id)
    return root / "users" / str(user_id) / HOOKS_DIR_NAME / hook_id / HOOK_FILE_NAME


def detail_to_record(
    detail: AssistantHookDetailDTO,
    *,
    path: Path,
    updated_at: datetime | None = None,
) -> StoredAssistantHook:
    return StoredAssistantHook(
        id=detail.id,
        name=detail.name,
        description=detail.description,
        enabled=detail.enabled,
        event=detail.event,
        action=_copy_hook_action(detail.action),
        updated_at=updated_at,
        path=path,
    )


def create_hook_detail(payload: AssistantHookCreateDTO, *, existing_ids: set[str]) -> AssistantHookDetailDTO:
    return AssistantHookDetailDTO(
        id=create_user_hook_id(payload.name, existing_ids=existing_ids),
        name=payload.name,
        description=normalize_optional_text(payload.description),
        enabled=payload.enabled,
        event=payload.event,
        action=normalize_hook_action(payload.action),
        updated_at=None,
    )


def update_hook_detail(
    hook_id: str,
    payload: AssistantHookUpdateDTO,
    *,
    updated_at: datetime | None,
) -> AssistantHookDetailDTO:
    return AssistantHookDetailDTO(
        id=hook_id,
        name=payload.name,
        description=normalize_optional_text(payload.description),
        enabled=payload.enabled,
        event=payload.event,
        action=normalize_hook_action(payload.action),
        updated_at=updated_at,
    )


def format_hook_document(detail: AssistantHookDetailDTO) -> str:
    document: dict[str, object] = {
        "id": detail.id,
        "name": detail.name,
        "description": detail.description,
        "author": USER_HOOK_AUTHOR,
        "enabled": detail.enabled,
        "trigger": {"event": detail.event, "node_types": []},
        "action": {
            "type": detail.action.action_type,
            "config": _build_hook_action_config(detail.action),
        },
        "priority": DEFAULT_HOOK_PRIORITY,
        "timeout": DEFAULT_HOOK_TIMEOUT,
    }
    if detail.description is None:
        document.pop("description")
    return yaml.safe_dump({YAML_ROOT_KEY_HOOK: document}, allow_unicode=True, sort_keys=False)


def parse_hook_document(path: Path, raw_text: str) -> StoredAssistantHook:
    loaded = yaml.safe_load(raw_text) or {}
    if not isinstance(loaded, dict):
        raise ConfigurationError(f"Assistant hook file must be a YAML object: {path}")
    hook = loaded.get(YAML_ROOT_KEY_HOOK)
    if not isinstance(hook, dict):
        raise ConfigurationError(f"Assistant hook file is missing hook root: {path}")
    _reject_unsupported_hook_fields(hook, path)
    hook_id = hook.get("id")
    name = hook.get("name")
    if not isinstance(hook_id, str) or not hook_id.strip():
        raise ConfigurationError(f"Assistant hook file is missing id: {path}")
    if not isinstance(name, str) or not name.strip():
        raise ConfigurationError(f"Assistant hook file is missing name: {path}")
    enabled = hook.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ConfigurationError(f"Assistant hook field 'enabled' must be a boolean: {path}")
    trigger = hook.get("trigger")
    if not isinstance(trigger, dict):
        raise ConfigurationError(f"Assistant hook trigger must be an object: {path}")
    event = trigger.get("event")
    if event not in {"before_assistant_response", "after_assistant_response"}:
        raise ConfigurationError(f"Assistant hook event is invalid: {path}")
    node_types = trigger.get("node_types", [])
    if node_types not in ([], None):
        raise ConfigurationError(f"Assistant hook node_types must stay empty: {path}")
    validate_hook_id(hook_id.strip())
    return StoredAssistantHook(
        id=hook_id.strip(),
        name=normalize_assistant_hook_name(name),
        description=normalize_optional_text(_read_optional_string(hook, "description", path)),
        enabled=enabled,
        event=event,
        action=_parse_hook_action(hook.get("action"), path),
        updated_at=datetime.fromtimestamp(path.stat().st_mtime, tz=UTC),
        path=path,
    )


def validate_hook_id(hook_id: str) -> None:
    if not HOOK_ID_PATTERN.fullmatch(hook_id):
        raise ConfigurationError(f"Assistant hook id is invalid: {hook_id}")


def create_user_hook_id(name: str, *, existing_ids: set[str]) -> str:
    base_slug = slugify_hook_name(name)
    while True:
        candidate = f"{USER_HOOK_ID_PREFIX}{base_slug}-{secrets.token_hex(3)}"
        if candidate not in existing_ids:
            return candidate


def normalize_hook_action(action: AssistantHookActionDTO) -> AssistantHookActionDTO:
    if action.action_type == "agent":
        return AssistantAgentHookActionDTO(
            action_type="agent",
            agent_id=normalize_hook_agent_id(action.agent_id),
            input_mapping=dict(action.input_mapping),
        )
    return AssistantMcpHookActionDTO(
        action_type="mcp",
        server_id=normalize_hook_mcp_server_id(action.server_id),
        tool_name=normalize_hook_mcp_tool_name(action.tool_name),
        arguments=dict(action.arguments),
        input_mapping=dict(action.input_mapping),
    )


def normalize_hook_agent_id(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise BusinessRuleError("Hook 需要绑定一个 Agent。")
    return normalized


def normalize_hook_mcp_server_id(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise BusinessRuleError("Hook 需要选择一个 MCP。")
    return normalized


def normalize_hook_mcp_tool_name(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise BusinessRuleError("Hook 需要填写工具名称。")
    return normalized


def slugify_hook_name(name: str) -> str:
    normalized = normalize_optional_text(name.lower()) or "chat-hook"
    slug = SLUG_PATTERN.sub("-", normalized).strip("-")
    return slug or "chat-hook"


def _copy_hook_action(action: AssistantHookActionDTO) -> AssistantHookActionDTO:
    return normalize_hook_action(action)


def _build_hook_action_config(action: AssistantHookActionDTO) -> dict[str, object]:
    if action.action_type == "agent":
        return {
            "agent_id": action.agent_id,
            "input_mapping": dict(action.input_mapping),
        }
    return {
        "server_id": action.server_id,
        "tool_name": action.tool_name,
        "arguments": dict(action.arguments),
        "input_mapping": dict(action.input_mapping),
    }


def _parse_hook_action(action: object, path: Path) -> AssistantHookActionDTO:
    if not isinstance(action, dict):
        raise ConfigurationError(f"Assistant hook action must be an object: {path}")
    action_type = action.get("type")
    config = action.get("config")
    if not isinstance(config, dict):
        raise ConfigurationError(f"Assistant hook action config must be an object: {path}")
    try:
        if action_type == "agent":
            return normalize_hook_action(
                AssistantAgentHookActionDTO.model_validate(
                    {
                        "action_type": "agent",
                        "agent_id": config.get("agent_id"),
                        "input_mapping": config.get("input_mapping", {}),
                    }
                )
            )
        if action_type == "mcp":
            return normalize_hook_action(
                AssistantMcpHookActionDTO.model_validate(
                    {
                        "action_type": "mcp",
                        "server_id": config.get("server_id"),
                        "tool_name": config.get("tool_name"),
                        "arguments": config.get("arguments", {}),
                        "input_mapping": config.get("input_mapping", {}),
                    }
                )
            )
    except ValidationError as exc:
        raise ConfigurationError(f"Assistant hook action config is invalid: {path}") from exc
    raise ConfigurationError(f"Assistant hook action type must be agent or mcp: {path}")


def _read_optional_string(metadata: dict, key: str, path: Path) -> str | None:
    value = metadata.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigurationError(f"Assistant hook field '{key}' must be a string: {path}")
    return value


def _reject_unsupported_hook_fields(hook: dict, path: Path) -> None:
    if hook.get("condition") is not None:
        raise ConfigurationError(f"Assistant hook condition is not supported yet: {path}")
    if hook.get("retry") is not None:
        raise ConfigurationError(f"Assistant hook retry is not supported yet: {path}")
