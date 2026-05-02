from __future__ import annotations

import json
from typing import Any

from app.modules.config_registry.schemas import ModelConfig, SkillConfig
from app.modules.config_registry.infrastructure.skill_input_validator import (
    SkillInputValidationError,
    validate_input_schema,
)
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError

from ..dto import (
    AssistantDocumentContextRecoverySnapshotDTO,
    AssistantDocumentContextProjectionMode,
    AssistantMessageDTO,
    AssistantProjectToolDiscoveryDecisionDTO,
    AssistantProjectToolGuidanceDTO,
)

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
PROJECT_SEARCH_GUIDANCE_TOOL_NAMES = (
    "project.search_documents",
    "project.read_documents",
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


def format_document_context(
    document_context_injection_snapshot: dict[str, Any] | None,
) -> str:
    projected_snapshot = build_document_context_prompt_snapshot(
        document_context_injection_snapshot
    )
    if projected_snapshot is None:
        return ""
    active_path, selected_paths = _extract_document_context_paths(projected_snapshot)
    lines: list[str] = []
    if active_path:
        lines.append(f"- 当前活动文稿：{active_path}")
    if selected_paths:
        lines.append("- 已选参考文稿：")
        lines.extend(f"  - {path}" for path in selected_paths)
    return "\n".join(
        [
            "【当前文稿上下文】",
            *lines,
            "如需查看这些文稿的真实内容，请调用 project.read_documents。",
        ]
    )


def build_document_context_prompt_snapshot(
    document_context: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(document_context, dict):
        return None
    active_path, selected_paths = _extract_document_context_paths(document_context)
    if not active_path and not selected_paths:
        return None
    payload: dict[str, Any] = {
        "active_path": active_path or None,
        "active_document_ref": _read_optional_string(document_context.get("active_document_ref")) or None,
        "active_binding_version": _read_optional_string(document_context.get("active_binding_version")) or None,
        "selected_paths": selected_paths,
        "selected_document_refs": _read_string_list(document_context.get("selected_document_refs")),
        "catalog_version": _read_optional_string(document_context.get("catalog_version")) or None,
    }
    active_buffer_state = document_context.get("active_buffer_state")
    if isinstance(active_buffer_state, dict):
        payload["active_buffer_state"] = active_buffer_state
    dto = AssistantDocumentContextRecoverySnapshotDTO.model_validate(payload)
    return dto.model_dump(mode="json")


def build_document_context_injection_snapshot(
    document_context: dict[str, Any] | None,
    *,
    document_context_recovery_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    source_document_context = (
        document_context_recovery_snapshot
        if isinstance(document_context_recovery_snapshot, dict)
        else document_context
    )
    return build_document_context_prompt_snapshot(source_document_context)


def resolve_document_context_projection_mode(
    projected_snapshot: dict[str, Any] | None,
) -> AssistantDocumentContextProjectionMode:
    active_path, selected_paths = _extract_document_context_paths(projected_snapshot)
    if active_path and selected_paths:
        return "full"
    if active_path:
        return "active_only"
    if selected_paths:
        return "selected_only"
    return "omitted"


def is_document_context_projection_collapsed(
    source_document_context: dict[str, Any] | None,
    projected_snapshot: dict[str, Any] | None,
) -> bool:
    source_projection = build_document_context_prompt_snapshot(source_document_context)
    if source_projection is None:
        return False
    return source_projection != projected_snapshot


def format_project_tool_guidance(
    *,
    has_project_scope: bool,
    latest_user_message: str | None = None,
    document_context: dict[str, Any] | None = None,
    visible_tool_names: tuple[str, ...] | None = None,
) -> str:
    snapshot = build_project_tool_guidance_snapshot(
        has_project_scope=has_project_scope,
        latest_user_message=latest_user_message,
        document_context=document_context,
        visible_tool_names=visible_tool_names,
    )
    return render_project_tool_guidance(snapshot)


def freeze_project_tool_guidance_snapshot(
    snapshot: AssistantProjectToolGuidanceDTO | None,
) -> dict[str, Any] | None:
    if snapshot is None:
        return None
    return snapshot.model_dump(mode="json")


def resolve_project_tool_discovery_decision(
    *,
    has_project_scope: bool,
    visible_tool_names: tuple[str, ...],
    latest_user_message: str | None = None,
    document_context: dict[str, Any] | None = None,
) -> AssistantProjectToolDiscoveryDecisionDTO | None:
    decision = _build_project_tool_discovery_candidate(
        has_project_scope=has_project_scope,
        latest_user_message=latest_user_message,
        document_context=document_context,
    )
    if decision is None:
        return None
    if not _all_guidance_tools_visible(decision.tool_names, visible_tool_names):
        return None
    return decision


def build_project_tool_guidance_snapshot(
    *,
    has_project_scope: bool,
    latest_user_message: str | None = None,
    document_context: dict[str, Any] | None = None,
    visible_tool_names: tuple[str, ...] | None = None,
) -> AssistantProjectToolGuidanceDTO | None:
    decision = resolve_project_tool_discovery_decision(
        has_project_scope=has_project_scope,
        visible_tool_names=visible_tool_names or PROJECT_SEARCH_GUIDANCE_TOOL_NAMES,
        latest_user_message=latest_user_message,
        document_context=document_context,
    )
    return build_project_tool_guidance_snapshot_from_discovery_decision(decision)


def build_project_tool_guidance_snapshot_from_discovery_decision(
    decision: AssistantProjectToolDiscoveryDecisionDTO | None,
) -> AssistantProjectToolGuidanceDTO | None:
    if decision is None:
        return None
    lines = [
        "- 当前对话已绑定项目。",
        "- 如果问题涉及跨文稿的一致性、人物关系、势力关系、时间轴、事件或伏笔回收，先调用 project.search_documents 缩小范围，再调用 project.read_documents 读取命中文稿。",
        "- 优先使用聚焦查询词：人物、人物关系、势力、势力关系、时间轴、事件、年表、伏笔、回收。",
        "- 如果本轮可使用 project.edit_document，小范围改动优先用它；old_text 必须结合 context_before/context_after 唯一定位，命中 0 处或多处都会失败。",
        "- 如果本轮可使用 project.write_document，content 必须是修改后的完整文稿全文，不要只传新增片段、diff、patch 或局部替换。",
    ]
    return AssistantProjectToolGuidanceDTO(
        guidance_type=decision.decision_type,
        tool_names=list(decision.tool_names),
        trigger_keywords=list(decision.trigger_keywords),
        discovery_source=decision.discovery_source,
        content="\n".join(["【项目范围工具提示】", *lines]),
    )


def _build_project_tool_discovery_candidate(
    *,
    has_project_scope: bool,
    latest_user_message: str | None = None,
    document_context: dict[str, Any] | None = None,
) -> AssistantProjectToolDiscoveryDecisionDTO | None:
    if not has_project_scope:
        return None
    active_path, selected_paths = _extract_document_context_paths(document_context)
    if active_path or selected_paths:
        return None
    trigger_keywords = _resolve_project_search_guidance_keywords(latest_user_message)
    if not trigger_keywords:
        return None
    return AssistantProjectToolDiscoveryDecisionDTO(
        decision_type="project_search_then_read",
        tool_names=list(PROJECT_SEARCH_GUIDANCE_TOOL_NAMES),
        trigger_keywords=trigger_keywords,
        discovery_source="continuity_keywords",
    )


def render_project_tool_guidance(
    snapshot: AssistantProjectToolGuidanceDTO | None,
) -> str:
    if snapshot is None:
        return ""
    return snapshot.content


def render_project_tool_guidance_snapshot(
    snapshot: dict[str, Any] | None,
) -> str:
    if snapshot is None:
        return ""
    return render_project_tool_guidance(
        AssistantProjectToolGuidanceDTO.model_validate(snapshot)
    )


def _all_guidance_tools_visible(
    tool_names: list[str],
    visible_tool_names: tuple[str, ...],
) -> bool:
    visible_set = set(visible_tool_names)
    return all(tool_name in visible_set for tool_name in tool_names)


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
    return bool(_resolve_project_search_guidance_keywords(latest_user_message))


def _resolve_project_search_guidance_keywords(
    latest_user_message: str | None,
) -> list[str]:
    if not isinstance(latest_user_message, str):
        return []
    normalized = latest_user_message.strip()
    if not normalized:
        return []
    return [keyword for keyword in PROJECT_SEARCH_GUIDANCE_KEYWORDS if keyword in normalized]


def _read_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]
