from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.schemas import HookConfig
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError, NotFoundError

from .query_dto import HookConfigUpdateDTO
from .write_validation_support import validate_config_model


def build_hook_config(payload: HookConfigUpdateDTO) -> HookConfig:
    document = payload.model_dump()
    action = document["action"]
    action["type"] = action.pop("action_type")
    return validate_config_model(HookConfig, document)


def ensure_matching_hook_id(path_hook_id: str, payload_hook_id: str) -> None:
    if payload_hook_id != path_hook_id:
        raise BusinessRuleError(
            f"Hook payload id '{payload_hook_id}' does not match path '{path_hook_id}'"
        )


def require_hook(config_loader: ConfigLoader, hook_id: str) -> HookConfig:
    try:
        return config_loader.load_hook(hook_id)
    except ConfigurationError as exc:
        if str(exc) == f"Hook not found: {hook_id}":
            raise NotFoundError(str(exc)) from exc
        raise


def serialize_hook_document(hook: HookConfig) -> dict[str, Any]:
    document = {
        "id": hook.id,
        "name": hook.name,
        "version": hook.version,
        "enabled": hook.enabled,
        "trigger": hook.trigger.model_dump(exclude_defaults=True, exclude_none=True),
        "action": hook.action.model_dump(by_alias=True, exclude_defaults=True, exclude_none=True),
        "priority": hook.priority,
        "timeout": hook.timeout,
    }
    if hook.description is not None:
        document["description"] = hook.description
    if hook.author is not None:
        document["author"] = hook.author
    if hook.condition is not None:
        document["condition"] = hook.condition.model_dump(exclude_defaults=True, exclude_none=True)
    if hook.retry is not None:
        document["retry"] = hook.retry.model_dump(exclude_defaults=True, exclude_none=True)
    document["action"]["config"] = deepcopy(document["action"]["config"])
    return document
