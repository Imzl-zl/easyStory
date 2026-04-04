from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable

from jinja2.exceptions import SecurityError, UndefinedError

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.schemas import AgentConfig, ModelConfig, SkillConfig
from app.shared.runtime import SkillTemplateRenderer
from app.shared.runtime.errors import ConfigurationError

from .assistant_hook_support import AssistantHookExecutionContext
from .assistant_prompt_support import (
    build_skill_variables,
    format_conversation_history,
    require_latest_user_message,
    resolve_model,
    validate_skill_input,
)
from .dto import AssistantTurnRequestDTO
from .preferences_dto import AssistantPreferencesDTO
from .preferences_support import apply_preferred_model


@dataclass(frozen=True)
class AssistantExecutionSpec:
    agent_id: str | None
    skill_id: str | None
    skill: SkillConfig | None
    system_prompt: str | None
    model: ModelConfig
    mcp_servers: list[str]


def resolve_execution_spec(
    config_loader: ConfigLoader,
    payload: AssistantTurnRequestDTO,
    preferences: AssistantPreferencesDTO,
    *,
    load_agent: Callable[[str], AgentConfig] | None = None,
    load_skill: Callable[[str], SkillConfig] | None = None,
) -> AssistantExecutionSpec:
    if payload.agent_id is not None:
        agent_loader = load_agent or config_loader.load_agent
        skill_loader = load_skill or config_loader.load_skill
        agent = agent_loader(payload.agent_id)
        skill = require_agent_skill(skill_loader, agent)
        preferred_model = apply_preferred_model(agent.model or skill.model, preferences)
        model = resolve_model(preferred_model, payload.model, context_label=agent.id)
        return AssistantExecutionSpec(
            agent_id=agent.id,
            skill_id=skill.id,
            skill=skill,
            system_prompt=agent.system_prompt,
            model=model,
            mcp_servers=list(agent.mcp_servers),
        )
    if payload.skill_id is None:
        preferred_model = apply_preferred_model(None, preferences)
        model = resolve_model(preferred_model, payload.model, context_label="assistant turn")
        return AssistantExecutionSpec(
            agent_id=None,
            skill_id=None,
            skill=None,
            system_prompt=None,
            model=model,
            mcp_servers=[],
        )
    skill_loader = load_skill or config_loader.load_skill
    skill = skill_loader(payload.skill_id)
    preferred_model = apply_preferred_model(skill.model, preferences)
    model = resolve_model(preferred_model, payload.model, context_label=skill.id)
    return AssistantExecutionSpec(
        agent_id=None,
        skill_id=skill.id,
        skill=skill,
        system_prompt=None,
        model=model,
        mcp_servers=[],
    )


def render_prompt(
    *,
    template_renderer: SkillTemplateRenderer,
    skill: SkillConfig | None,
    payload: AssistantTurnRequestDTO,
) -> str:
    if skill is None:
        return render_message_only_prompt(payload.messages)
    referenced_variables = template_renderer.referenced_variables(skill.prompt)
    variables = build_skill_variables(skill, payload.messages, payload.input_data)
    validate_skill_input(skill, variables)
    try:
        return render_skill_prompt(
            rendered_skill_prompt=template_renderer.render(skill.prompt, variables),
            messages=payload.messages,
            referenced_variables=referenced_variables,
        )
    except (SecurityError, UndefinedError) as exc:
        raise ConfigurationError(f"Assistant prompt render failed: {exc}") from exc


def render_message_only_prompt(messages: list[Any]) -> str:
    return render_message_context_sections(messages)


def render_skill_prompt(
    *,
    rendered_skill_prompt: str,
    messages: list[Any],
    referenced_variables: set[str],
) -> str:
    sections = [f"【当前 Skill 指令】\n{rendered_skill_prompt.strip()}"]
    if "messages_json" in referenced_variables:
        return "\n\n".join(section for section in sections if section.strip())
    latest_user_message = require_latest_user_message(messages)
    history = format_conversation_history(messages[:-1])
    if history and "conversation_history" not in referenced_variables:
        sections.append(f"【当前会话历史】\n{history}")
    if "user_input" not in referenced_variables:
        sections.append(f"【用户当前消息】\n{latest_user_message}")
    return "\n\n".join(section for section in sections if section.strip())


def render_message_context_sections(messages: list[Any]) -> str:
    latest_user_message = require_latest_user_message(messages)
    sections = [f"【用户当前消息】\n{latest_user_message}"]
    history = format_conversation_history(messages[:-1])
    if history:
        sections.insert(0, f"【当前会话历史】\n{history}")
    return "\n\n".join(sections)


def require_agent_skill(skill_loader: Callable[[str], SkillConfig], agent: AgentConfig) -> SkillConfig:
    if not agent.skills:
        raise ConfigurationError(f"Agent {agent.id} has no skills configured")
    return skill_loader(agent.skills[0])


def build_hook_agent_variables(
    context: AssistantHookExecutionContext,
    input_mapping: dict[str, str],
) -> dict[str, Any]:
    variables: dict[str, Any] = {
        "payload": context.payload,
        "payload_json": context.payload_json(),
        "event": context.event,
        "assistant_agent_id": context.assistant_agent_id,
        "assistant_skill_id": context.assistant_skill_id,
        "user_input": _resolve_hook_user_input(context),
        "conversation_history": _render_hook_conversation_history(context),
        "response_content": _read_optional_hook_text(context, "response.content"),
    }
    for target, source in input_mapping.items():
        variables[target] = context.read_path(source)
    return variables


def resolve_hook_agent_model(
    *,
    agent: AgentConfig,
    skill: SkillConfig,
    preferences: AssistantPreferencesDTO,
    assistant_model: ModelConfig,
) -> ModelConfig:
    hook_base_model = agent.model or skill.model
    if hook_base_model is None:
        return assistant_model.model_copy(deep=True)
    preferred_model = apply_preferred_model(hook_base_model, preferences)
    return resolve_model(preferred_model, None, context_label=f"Hook agent {agent.id}")


def hook_agent_response_format(agent: AgentConfig) -> str:
    if agent.output_schema is not None or agent.agent_type == "reviewer":
        return "json_object"
    return "text"


def resolve_hook_agent_output(agent: AgentConfig, content: Any) -> Any:
    if hook_agent_response_format(agent) == "json_object":
        return parse_json_output(content)
    return require_text_output(content)


def require_text_output(content: Any) -> str:
    if not isinstance(content, str):
        raise ConfigurationError("Assistant output must be plain text")
    return content


def parse_json_output(content: Any) -> Any:
    if isinstance(content, dict | list):
        return content
    if isinstance(content, str):
        parsed = _load_json_output(content)
        if isinstance(parsed, dict | list):
            return parsed
    raise ConfigurationError("Hook agent JSON output must be an object or array")


def validate_retry_policy(attempts: int, delay: int) -> None:
    if attempts < 1:
        raise ConfigurationError("Hook retry.max_attempts must be >= 1")
    if delay < 0:
        raise ConfigurationError("Hook retry.delay must be >= 0")


def _load_json_output(content: str) -> Any:
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise ConfigurationError("Hook agent JSON output must be valid JSON") from exc


def _resolve_hook_user_input(context: AssistantHookExecutionContext) -> str:
    if context.event == "after_assistant_response":
        response_content = _read_optional_hook_text(context, "response.content")
        if response_content:
            return response_content
    return _read_optional_hook_text(context, "request.user_input")


def _render_hook_conversation_history(context: AssistantHookExecutionContext) -> str:
    messages = _read_optional_hook_messages(context)
    if not messages:
        return ""
    return "\n\n".join(
        f"{_resolve_hook_message_role(message.get('role'))}：{message.get('content', '')}"
        for message in messages
    )


def _read_optional_hook_messages(context: AssistantHookExecutionContext) -> list[dict[str, Any]]:
    try:
        value = context.read_path("conversation.messages")
    except ConfigurationError:
        return []
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _read_optional_hook_text(context: AssistantHookExecutionContext, path: str) -> str:
    try:
        value = context.read_path(path)
    except ConfigurationError:
        return ""
    return value if isinstance(value, str) else ""


def _resolve_hook_message_role(role: object) -> str:
    if role == "assistant":
        return "助手"
    if role == "system":
        return "系统"
    return "用户"
