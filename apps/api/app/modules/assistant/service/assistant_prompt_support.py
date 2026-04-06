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
PROJECT_SEARCH_GUIDANCE_KEYWORDS = (
    "连续性",
    "一致性",
    "贯穿全文",
    "人物关系",
    "势力关系",
    "时间轴",
    "时间线",
    "事件",
    "年表",
    "伏笔",
    "回收",
)


def build_skill_variables(
    skill: SkillConfig,
    messages: list[AssistantMessageDTO],
    input_data: dict[str, Any],
    *,
    conversation_history_messages: list[AssistantMessageDTO] | None = None,
    compacted_context_summary: str | None = None,
) -> dict[str, Any]:
    declared = skill.inputs or skill.variables
    variables = {name: input_data[name] for name in declared if name in input_data}
    if USER_INPUT_VARIABLE in declared and USER_INPUT_VARIABLE not in variables:
        variables[USER_INPUT_VARIABLE] = require_latest_user_message(messages)
    if CONVERSATION_HISTORY_VARIABLE in declared and CONVERSATION_HISTORY_VARIABLE not in variables:
        variables[CONVERSATION_HISTORY_VARIABLE] = build_conversation_history_projection(
            conversation_history_messages
            if conversation_history_messages is not None
            else messages[:-1],
            compacted_context_summary=compacted_context_summary,
        )
    if MESSAGES_JSON_VARIABLE in declared and MESSAGES_JSON_VARIABLE not in variables:
        variables[MESSAGES_JSON_VARIABLE] = json.dumps(
            [item.model_dump(mode="json") for item in messages],
            ensure_ascii=False,
        )
    return variables


def format_conversation_history(messages: list[AssistantMessageDTO]) -> str:
    formatted = [_format_message(item) for item in messages]
    return "\n\n".join(item for item in formatted if item)


def build_conversation_history_projection(
    messages: list[AssistantMessageDTO],
    *,
    compacted_context_summary: str | None = None,
) -> str:
    sections: list[str] = []
    if isinstance(compacted_context_summary, str) and compacted_context_summary.strip():
        sections.append(
            "\n".join(
                [
                    "【压缩后的早期对话摘要】",
                    compacted_context_summary.strip(),
                ]
            )
        )
    history = format_conversation_history(messages)
    if history:
        sections.append(history)
    return "\n\n".join(section for section in sections if section.strip())


def require_latest_user_message(messages: list[AssistantMessageDTO]) -> str:
    if messages[-1].role != "user":
        raise BusinessRuleError("assistant 对话最后一条消息必须是 user")
    return messages[-1].content


def format_document_context(document_context: dict[str, Any] | None) -> str:
    active_path, selected_paths = _extract_document_context_paths(document_context)
    lines: list[str] = []
    if active_path:
        lines.append(f"- 当前活动文稿：{active_path}")
    if selected_paths:
        lines.append("- 已选参考文稿：")
        lines.extend(f"  - {path}" for path in selected_paths)
    if not lines:
        return ""
    return "\n".join(
        [
            "【当前文稿上下文】",
            *lines,
            "如需查看这些文稿的真实内容，请调用 project.read_documents。",
        ]
    )


def format_project_tool_guidance(
    *,
    has_project_scope: bool,
    latest_user_message: str | None = None,
    document_context: dict[str, Any] | None = None,
) -> str:
    if not has_project_scope:
        return ""
    active_path, selected_paths = _extract_document_context_paths(document_context)
    if active_path or selected_paths:
        return ""
    if not _should_hint_project_search(latest_user_message):
        return ""
    lines = [
        "- 当前对话已绑定项目。",
        "- 如果问题涉及跨文稿的一致性、人物关系、势力关系、时间轴、事件或伏笔回收，先调用 project.search_documents 缩小范围，再调用 project.read_documents 读取命中文稿。",
        "- 优先使用聚焦查询词：人物、人物关系、势力、势力关系、时间轴、事件、年表、伏笔、回收。",
    ]
    return "\n".join(["【项目范围工具提示】", *lines])


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
                update=override.model_dump(
                    mode="json",
                    exclude_none=True,
                    exclude_unset=True,
                )
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


def _read_optional_string(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _extract_document_context_paths(document_context: dict[str, Any] | None) -> tuple[str, list[str]]:
    if not isinstance(document_context, dict):
        return "", []
    return (
        _read_optional_string(document_context.get("active_path")),
        _read_string_list(document_context.get("selected_paths")),
    )


def _should_hint_project_search(latest_user_message: str | None) -> bool:
    if not isinstance(latest_user_message, str):
        return False
    normalized = latest_user_message.strip()
    if not normalized:
        return False
    return any(keyword in normalized for keyword in PROJECT_SEARCH_GUIDANCE_KEYWORDS)


def _read_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]
