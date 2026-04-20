from __future__ import annotations

from typing import Any

from jinja2.exceptions import SecurityError, UndefinedError

from app.modules.config_registry.schemas import SkillConfig
from app.shared.runtime.template_renderer import SkillTemplateRenderer
from app.shared.runtime.errors import ConfigurationError

from ..dto import AssistantTurnRequestDTO
from .assistant_prompt_support import (
    build_conversation_history_projection,
    build_skill_variables,
    format_document_context,
    render_project_tool_guidance_snapshot,
    require_latest_user_message,
    validate_skill_input,
)


def render_prompt(
    *,
    template_renderer: SkillTemplateRenderer,
    skill: SkillConfig | None,
    payload: AssistantTurnRequestDTO,
    document_context_injection_snapshot: dict[str, Any] | None = None,
    tool_guidance_snapshot: dict[str, Any] | None = None,
    projected_messages: list[Any] | None = None,
    compacted_context_summary: str | None = None,
) -> str:
    messages = list(projected_messages or payload.messages)
    if skill is None:
        return render_message_only_prompt(
            messages,
            document_context_injection_snapshot=document_context_injection_snapshot,
            tool_guidance_snapshot=tool_guidance_snapshot,
            compacted_context_summary=compacted_context_summary,
        )
    referenced_variables = template_renderer.referenced_variables(skill.prompt)
    variables = build_skill_variables(
        skill,
        payload.messages,
        payload.input_data,
        conversation_history_messages=messages[:-1],
        compacted_context_summary=compacted_context_summary,
    )
    validate_skill_input(skill, variables)
    try:
        return render_skill_prompt(
            rendered_skill_prompt=template_renderer.render(skill.prompt, variables),
            messages=messages,
            referenced_variables=referenced_variables,
            document_context_injection_snapshot=document_context_injection_snapshot,
            tool_guidance_snapshot=tool_guidance_snapshot,
            compacted_context_summary=compacted_context_summary,
        )
    except (SecurityError, UndefinedError) as exc:
        raise ConfigurationError(f"Assistant prompt render failed: {exc}") from exc


def render_message_only_prompt(
    messages: list[Any],
    *,
    document_context_injection_snapshot: dict[str, Any] | None = None,
    tool_guidance_snapshot: dict[str, Any] | None = None,
    compacted_context_summary: str | None = None,
) -> str:
    return render_message_context_sections(
        messages,
        document_context_injection_snapshot=document_context_injection_snapshot,
        tool_guidance_snapshot=tool_guidance_snapshot,
        compacted_context_summary=compacted_context_summary,
    )


def render_skill_prompt(
    *,
    rendered_skill_prompt: str,
    messages: list[Any],
    referenced_variables: set[str],
    document_context_injection_snapshot: dict[str, Any] | None = None,
    tool_guidance_snapshot: dict[str, Any] | None = None,
    compacted_context_summary: str | None = None,
) -> str:
    sections = [f"【当前 Skill 指令】\n{rendered_skill_prompt.strip()}"]
    latest_user_message = require_latest_user_message(messages)
    if "messages_json" in referenced_variables:
        sections.extend(
            _build_project_context_sections(
                document_context_injection_snapshot=document_context_injection_snapshot,
                tool_guidance_snapshot=tool_guidance_snapshot,
            )
        )
        return "\n\n".join(section for section in sections if section.strip())
    history = build_conversation_history_projection(
        messages[:-1],
        compacted_context_summary=compacted_context_summary,
    )
    if history and "conversation_history" not in referenced_variables:
        sections.append(f"【当前会话历史】\n{history}")
    sections.extend(
        _build_project_context_sections(
            document_context_injection_snapshot=document_context_injection_snapshot,
            tool_guidance_snapshot=tool_guidance_snapshot,
        )
    )
    if "user_input" not in referenced_variables:
        sections.append(f"【用户当前消息】\n{latest_user_message}")
    return "\n\n".join(section for section in sections if section.strip())


def render_message_context_sections(
    messages: list[Any],
    *,
    document_context_injection_snapshot: dict[str, Any] | None = None,
    tool_guidance_snapshot: dict[str, Any] | None = None,
    compacted_context_summary: str | None = None,
) -> str:
    latest_user_message = require_latest_user_message(messages)
    sections = [f"【用户当前消息】\n{latest_user_message}"]
    history = build_conversation_history_projection(
        messages[:-1],
        compacted_context_summary=compacted_context_summary,
    )
    if history:
        sections.insert(0, f"【当前会话历史】\n{history}")
    project_sections = _build_project_context_sections(
        document_context_injection_snapshot=document_context_injection_snapshot,
        tool_guidance_snapshot=tool_guidance_snapshot,
    )
    if project_sections:
        sections = [*sections[:-1], *project_sections, sections[-1]]
    return "\n\n".join(sections)


def _build_project_context_sections(
    *,
    document_context_injection_snapshot: dict[str, Any] | None,
    tool_guidance_snapshot: dict[str, Any] | None,
) -> list[str]:
    sections: list[str] = []
    document_context_section = format_document_context(
        document_context_injection_snapshot
    )
    if document_context_section:
        sections.append(document_context_section)
    if tool_guidance_snapshot:
        sections.append(render_project_tool_guidance_snapshot(tool_guidance_snapshot))
    return sections
