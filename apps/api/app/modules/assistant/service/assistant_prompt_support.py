from __future__ import annotations

import json
from typing import Any

from app.modules.config_registry.schemas import ModelConfig, SkillConfig
from app.modules.config_registry.infrastructure.skill_input_validator import (
    SkillInputValidationError,
    validate_input_schema,
)
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError

from .dto import AssistantMessageDTO

USER_INPUT_VARIABLE = "user_input"
CONVERSATION_HISTORY_VARIABLE = "conversation_history"
MESSAGES_JSON_VARIABLE = "messages_json"


def build_skill_variables(
    skill: SkillConfig,
    messages: list[AssistantMessageDTO],
    input_data: dict[str, Any],
) -> dict[str, Any]:
    declared = skill.inputs or skill.variables
    variables = {name: input_data[name] for name in declared if name in input_data}
    if USER_INPUT_VARIABLE in declared and USER_INPUT_VARIABLE not in variables:
        variables[USER_INPUT_VARIABLE] = require_latest_user_message(messages)
    if CONVERSATION_HISTORY_VARIABLE in declared and CONVERSATION_HISTORY_VARIABLE not in variables:
        variables[CONVERSATION_HISTORY_VARIABLE] = format_conversation_history(messages[:-1])
    if MESSAGES_JSON_VARIABLE in declared and MESSAGES_JSON_VARIABLE not in variables:
        variables[MESSAGES_JSON_VARIABLE] = json.dumps(
            [item.model_dump(mode="json") for item in messages],
            ensure_ascii=False,
        )
    return variables


def format_conversation_history(messages: list[AssistantMessageDTO]) -> str:
    formatted = [_format_message(item) for item in messages]
    return "\n\n".join(item for item in formatted if item)


def require_latest_user_message(messages: list[AssistantMessageDTO]) -> str:
    if messages[-1].role != "user":
        raise BusinessRuleError("assistant 对话最后一条消息必须是 user")
    return messages[-1].content


def resolve_model(
    base_model: ModelConfig | None,
    override: ModelConfig | None,
    *,
    context_label: str,
) -> ModelConfig:
    resolved = base_model.model_copy(deep=True) if base_model is not None else ModelConfig()
    if override is not None:
        if override.provider is not None and override.provider != resolved.provider:
            resolved = resolved.model_copy(
                update={
                    "provider": override.provider,
                    "name": override.name,
                }
            )
        else:
            resolved = resolved.model_copy(
                update=override.model_dump(mode="json", exclude_none=True)
            )
    if not resolved.provider:
        raise ConfigurationError(f"{context_label} is missing executable model provider")
    return resolved


def validate_skill_input(skill: SkillConfig, input_data: dict[str, Any]) -> None:
    declared = skill.inputs or skill.variables
    try:
        validate_input_schema(declared, input_data)
    except SkillInputValidationError as exc:
        raise ConfigurationError(str(exc)) from exc


def _format_message(message: AssistantMessageDTO) -> str:
    if message.role == "assistant":
        return f"助手：{message.content}"
    return f"用户：{message.content}"
