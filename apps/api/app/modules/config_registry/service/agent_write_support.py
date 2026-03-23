from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.schemas import AgentConfig, ModelConfig
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError, NotFoundError

from .query_dto import AgentConfigUpdateDTO


def build_agent_config(payload: AgentConfigUpdateDTO) -> AgentConfig:
    document = payload.model_dump()
    document["type"] = document.pop("agent_type")
    document["skills"] = document.pop("skill_ids")
    return AgentConfig.model_validate(document)


def ensure_matching_agent_id(path_agent_id: str, payload_agent_id: str) -> None:
    if payload_agent_id != path_agent_id:
        raise BusinessRuleError(
            f"Agent payload id '{payload_agent_id}' does not match path '{path_agent_id}'"
        )


def require_agent(config_loader: ConfigLoader, agent_id: str) -> AgentConfig:
    try:
        return config_loader.load_agent(agent_id)
    except ConfigurationError as exc:
        if str(exc) == f"Agent not found: {agent_id}":
            raise NotFoundError(str(exc)) from exc
        raise


def serialize_agent_document(agent: AgentConfig) -> dict[str, Any]:
    document = {
        "id": agent.id,
        "name": agent.name,
        "version": agent.version,
        "type": agent.agent_type,
        "system_prompt": agent.system_prompt,
        "skills": list(agent.skills),
        "mcp_servers": list(agent.mcp_servers),
    }
    if agent.description is not None:
        document["description"] = agent.description
    if agent.author is not None:
        document["author"] = agent.author
    if agent.tags:
        document["tags"] = list(agent.tags)
    if agent.output_schema is not None:
        document["output_schema"] = deepcopy(agent.output_schema)
    if agent.model is not None:
        document["model"] = _dump_model(agent.model)
    return document


def _dump_model(model: ModelConfig) -> dict[str, Any]:
    return model.model_dump(
        exclude_defaults=True,
        exclude_none=True,
    )
