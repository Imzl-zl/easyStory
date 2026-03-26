from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
import uuid

from jinja2.exceptions import SecurityError, UndefinedError

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.schemas import AgentConfig, ModelConfig, SkillConfig
from app.shared.runtime import SkillTemplateRenderer
from app.shared.runtime.errors import ConfigurationError

from .assistant_hook_support import AssistantHookExecutionContext, build_assistant_hook_payload
from .assistant_prompt_support import build_skill_variables, resolve_model
from .dto import AssistantHookResultDTO, AssistantTurnRequestDTO, AssistantTurnResponseDTO


@dataclass(frozen=True)
class AssistantExecutionSpec:
    agent_id: str | None
    skill: SkillConfig
    system_prompt: str | None
    model: ModelConfig
    mcp_servers: list[str]


def resolve_execution_spec(
    config_loader: ConfigLoader,
    payload: AssistantTurnRequestDTO,
) -> AssistantExecutionSpec:
    if payload.agent_id is not None:
        agent = config_loader.load_agent(payload.agent_id)
        skill = require_agent_skill(config_loader, agent)
        model = resolve_model(agent.model or skill.model, payload.model, context_label=agent.id)
        return AssistantExecutionSpec(
            agent_id=agent.id,
            skill=skill,
            system_prompt=agent.system_prompt,
            model=model,
            mcp_servers=list(agent.mcp_servers),
        )
    skill = config_loader.load_skill(payload.skill_id or "")
    model = resolve_model(skill.model, payload.model, context_label=skill.id)
    return AssistantExecutionSpec(
        agent_id=None,
        skill=skill,
        system_prompt=None,
        model=model,
        mcp_servers=[],
    )


def render_prompt(
    *,
    config_loader: ConfigLoader,
    template_renderer: SkillTemplateRenderer,
    skill: SkillConfig,
    payload: AssistantTurnRequestDTO,
) -> str:
    variables = build_skill_variables(skill, payload.messages, payload.input_data)
    config_loader.validate_skill_input(skill, variables)
    try:
        return template_renderer.render(skill.prompt, variables)
    except (SecurityError, UndefinedError) as exc:
        raise ConfigurationError(f"Assistant prompt render failed: {exc}") from exc


def require_agent_skill(config_loader: ConfigLoader, agent: AgentConfig) -> SkillConfig:
    if not agent.skills:
        raise ConfigurationError(f"Agent {agent.id} has no skills configured")
    return config_loader.load_skill(agent.skills[0])


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
    }
    for target, source in input_mapping.items():
        variables[target] = context.read_path(source)
    return variables


def dump_turn_messages(payload: AssistantTurnRequestDTO) -> list[dict[str, str]]:
    return [item.model_dump(mode="json") for item in payload.messages]


def build_before_assistant_payload(
    spec: AssistantExecutionSpec,
    payload: AssistantTurnRequestDTO,
    project_id: uuid.UUID | None,
    messages: list[dict[str, str]],
) -> dict[str, Any]:
    return build_assistant_hook_payload(
        event="before_assistant_response",
        agent_id=spec.agent_id,
        skill_id=spec.skill.id,
        project_id=project_id,
        messages=messages,
        input_data=payload.input_data,
        mcp_servers=spec.mcp_servers,
    )


def build_after_assistant_payload(
    spec: AssistantExecutionSpec,
    payload: AssistantTurnRequestDTO,
    project_id: uuid.UUID | None,
    messages: list[dict[str, str]],
    content: str,
) -> dict[str, Any]:
    return build_assistant_hook_payload(
        event="after_assistant_response",
        agent_id=spec.agent_id,
        skill_id=spec.skill.id,
        project_id=project_id,
        messages=messages,
        input_data=payload.input_data,
        mcp_servers=spec.mcp_servers,
        extra={"response": {"content": content}},
    )


def build_turn_response(
    spec: AssistantExecutionSpec,
    raw_output: dict[str, Any],
    content: str,
    hook_results: list[AssistantHookResultDTO],
) -> AssistantTurnResponseDTO:
    return AssistantTurnResponseDTO(
        agent_id=spec.agent_id,
        skill_id=spec.skill.id,
        provider=spec.model.provider or "",
        model_name=raw_output.get("model_name") or spec.model.name or "",
        content=content,
        hook_results=hook_results,
        mcp_servers=spec.mcp_servers,
        input_tokens=raw_output.get("input_tokens"),
        output_tokens=raw_output.get("output_tokens"),
        total_tokens=raw_output.get("total_tokens"),
    )


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
