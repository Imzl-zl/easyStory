from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import re
import secrets

import yaml

from app.modules.config_registry.schemas import AgentConfig, ModelConfig
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError

from .assistant_agent_dto import (
    AssistantAgentCreateDTO,
    AssistantAgentDetailDTO,
    AssistantAgentSummaryDTO,
    AssistantAgentUpdateDTO,
    normalize_assistant_agent_name,
)
from .preferences_support import normalize_optional_text

AGENT_FILE_NAME = "AGENT.md"
AGENTS_DIR_NAME = "agents"
FRONTMATTER_BOUNDARY = "---"
USER_AGENT_AUTHOR = "user"
USER_AGENT_CATEGORY = "writer"
USER_AGENT_ID_PREFIX = "agent.user."
AGENT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class StoredAssistantAgent:
    id: str
    name: str
    description: str | None
    enabled: bool
    skill_id: str
    system_prompt: str
    default_provider: str | None
    default_model_name: str | None
    default_max_output_tokens: int | None
    updated_at: datetime | None
    path: Path


def build_agent_summary(record: StoredAssistantAgent) -> AssistantAgentSummaryDTO:
    return AssistantAgentSummaryDTO(
        id=record.id,
        file_name=record.path.name,
        name=record.name,
        description=record.description,
        enabled=record.enabled,
        skill_id=record.skill_id,
        updated_at=record.updated_at,
    )


def build_agent_detail(record: StoredAssistantAgent) -> AssistantAgentDetailDTO:
    return AssistantAgentDetailDTO(
        id=record.id,
        file_name=record.path.name,
        name=record.name,
        description=record.description,
        enabled=record.enabled,
        skill_id=record.skill_id,
        system_prompt=record.system_prompt,
        default_provider=record.default_provider,
        default_model_name=record.default_model_name,
        default_max_output_tokens=record.default_max_output_tokens,
        updated_at=record.updated_at,
    )


def build_runtime_agent(record: StoredAssistantAgent) -> AgentConfig:
    payload: dict[str, object] = {
        "id": record.id,
        "name": record.name,
        "type": USER_AGENT_CATEGORY,
        "description": record.description,
        "author": USER_AGENT_AUTHOR,
        "system_prompt": record.system_prompt,
        "skills": [record.skill_id],
        "mcp_servers": [],
    }
    model = build_agent_model(record)
    if model is not None:
        payload["model"] = model.model_dump(mode="json", exclude_none=True)
    return AgentConfig.model_validate(payload)


def build_agent_path(root: Path, user_id, agent_id: str) -> Path:
    validate_agent_id(agent_id)
    return root / "users" / str(user_id) / AGENTS_DIR_NAME / agent_id / AGENT_FILE_NAME


def detail_to_record(
    detail: AssistantAgentDetailDTO,
    *,
    path: Path,
    updated_at: datetime | None = None,
) -> StoredAssistantAgent:
    return StoredAssistantAgent(
        id=detail.id,
        name=detail.name,
        description=detail.description,
        enabled=detail.enabled,
        skill_id=detail.skill_id,
        system_prompt=detail.system_prompt,
        default_provider=detail.default_provider,
        default_model_name=detail.default_model_name,
        default_max_output_tokens=detail.default_max_output_tokens,
        updated_at=updated_at,
        path=path,
    )


def create_agent_detail(payload: AssistantAgentCreateDTO, *, existing_ids: set[str]) -> AssistantAgentDetailDTO:
    return AssistantAgentDetailDTO(
        id=create_user_agent_id(payload.name, existing_ids=existing_ids),
        name=payload.name,
        description=normalize_optional_text(payload.description),
        enabled=payload.enabled,
        skill_id=normalize_agent_skill_id(payload.skill_id),
        system_prompt=normalize_agent_system_prompt(payload.system_prompt),
        default_provider=normalize_optional_text(payload.default_provider),
        default_model_name=normalize_optional_text(payload.default_model_name),
        default_max_output_tokens=payload.default_max_output_tokens,
        updated_at=None,
    )


def update_agent_detail(
    agent_id: str,
    payload: AssistantAgentUpdateDTO,
    *,
    updated_at: datetime | None,
) -> AssistantAgentDetailDTO:
    return AssistantAgentDetailDTO(
        id=agent_id,
        name=payload.name,
        description=normalize_optional_text(payload.description),
        enabled=payload.enabled,
        skill_id=normalize_agent_skill_id(payload.skill_id),
        system_prompt=normalize_agent_system_prompt(payload.system_prompt),
        default_provider=normalize_optional_text(payload.default_provider),
        default_model_name=normalize_optional_text(payload.default_model_name),
        default_max_output_tokens=payload.default_max_output_tokens,
        updated_at=updated_at,
    )


def format_agent_markdown(detail: AssistantAgentDetailDTO) -> str:
    metadata = {
        "id": detail.id,
        "name": detail.name,
        "enabled": detail.enabled,
        "skill_id": detail.skill_id,
    }
    if detail.description is not None:
        metadata["description"] = detail.description
    model = dump_agent_model(detail)
    if model:
        metadata["model"] = model
    metadata_text = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).strip()
    return (
        f"{FRONTMATTER_BOUNDARY}\n{metadata_text}\n{FRONTMATTER_BOUNDARY}\n\n"
        f"{normalize_agent_system_prompt(detail.system_prompt)}\n"
    )


def parse_agent_markdown(path: Path, raw_text: str) -> StoredAssistantAgent:
    metadata, content = split_frontmatter(raw_text, path)
    agent_id = metadata.get("id")
    name = metadata.get("name")
    if not isinstance(agent_id, str) or not agent_id.strip():
        raise ConfigurationError(f"Assistant agent file is missing id: {path}")
    if not isinstance(name, str) or not name.strip():
        raise ConfigurationError(f"Assistant agent file is missing name: {path}")
    validate_agent_id(agent_id.strip())
    enabled = metadata.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ConfigurationError(f"Assistant agent field 'enabled' must be a boolean: {path}")
    skill_id = metadata.get("skill_id")
    if not isinstance(skill_id, str) or not skill_id.strip():
        raise ConfigurationError(f"Assistant agent file is missing skill_id: {path}")
    provider, model_name, max_output_tokens = parse_agent_model(metadata.get("model"), path)
    return StoredAssistantAgent(
        id=agent_id.strip(),
        name=normalize_assistant_agent_name(name),
        description=normalize_optional_text(read_optional_string(metadata, "description", path)),
        enabled=enabled,
        skill_id=normalize_agent_skill_id(skill_id),
        system_prompt=normalize_agent_system_prompt(content),
        default_provider=provider,
        default_model_name=model_name,
        default_max_output_tokens=max_output_tokens,
        updated_at=datetime.fromtimestamp(path.stat().st_mtime, tz=UTC),
        path=path,
    )


def validate_agent_id(agent_id: str) -> None:
    if not AGENT_ID_PATTERN.fullmatch(agent_id):
        raise ConfigurationError(f"Assistant agent id is invalid: {agent_id}")


def create_user_agent_id(name: str, *, existing_ids: set[str]) -> str:
    base_slug = slugify_agent_name(name)
    while True:
        candidate = f"{USER_AGENT_ID_PREFIX}{base_slug}-{secrets.token_hex(3)}"
        if candidate not in existing_ids:
            return candidate


def normalize_agent_skill_id(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise BusinessRuleError("Agent 需要绑定一个 Skill")
    return normalized


def normalize_agent_system_prompt(value: str) -> str:
    normalized = value.replace("\r\n", "\n").strip()
    if not normalized:
        raise BusinessRuleError("Agent 的系统提示不能为空")
    return normalized


def split_frontmatter(raw_text: str, path: Path) -> tuple[dict, str]:
    normalized = raw_text.replace("\r\n", "\n")
    if not normalized.startswith(f"{FRONTMATTER_BOUNDARY}\n"):
        raise ConfigurationError(f"Assistant agent file must start with frontmatter: {path}")
    parts = normalized.split(f"\n{FRONTMATTER_BOUNDARY}\n", maxsplit=1)
    if len(parts) != 2:
        raise ConfigurationError(f"Assistant agent file frontmatter is not properly closed: {path}")
    metadata_text = parts[0].removeprefix(f"{FRONTMATTER_BOUNDARY}\n")
    metadata = yaml.safe_load(metadata_text) or {}
    if not isinstance(metadata, dict):
        raise ConfigurationError(f"Assistant agent frontmatter must be a YAML object: {path}")
    return metadata, parts[1]


def read_optional_string(metadata: dict, key: str, path: Path) -> str | None:
    value = metadata.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigurationError(f"Assistant agent field '{key}' must be a string: {path}")
    return value


def parse_agent_model(model: object, path: Path) -> tuple[str | None, str | None, int | None]:
    if model is None:
        return None, None, None
    if not isinstance(model, dict):
        raise ConfigurationError(f"Assistant agent model frontmatter must be an object: {path}")
    provider = normalize_optional_text(read_optional_string(model, "provider", path))
    model_name = normalize_optional_text(read_optional_string(model, "name", path))
    max_output_tokens = model.get("max_tokens")
    if isinstance(max_output_tokens, bool) or (
        max_output_tokens is not None and not isinstance(max_output_tokens, int)
    ):
        raise ConfigurationError(f"Assistant agent model max_tokens must be an integer: {path}")
    return provider, model_name, max_output_tokens


def build_agent_model(record: StoredAssistantAgent) -> ModelConfig | None:
    if (
        record.default_provider is None
        and record.default_model_name is None
        and record.default_max_output_tokens is None
    ):
        return None
    payload: dict[str, object] = {}
    if record.default_provider is not None:
        payload["provider"] = record.default_provider
    if record.default_model_name is not None:
        payload["name"] = record.default_model_name
    if record.default_max_output_tokens is not None:
        payload["max_tokens"] = record.default_max_output_tokens
    return ModelConfig.model_validate(payload)


def dump_agent_model(detail: AssistantAgentDetailDTO) -> dict[str, object]:
    payload: dict[str, object] = {}
    if detail.default_provider is not None:
        payload["provider"] = detail.default_provider
    if detail.default_model_name is not None:
        payload["name"] = detail.default_model_name
    if detail.default_max_output_tokens is not None:
        payload["max_tokens"] = detail.default_max_output_tokens
    return payload


def slugify_agent_name(name: str) -> str:
    normalized = normalize_optional_text(name.lower()) or "chat-agent"
    slug = SLUG_PATTERN.sub("-", normalized).strip("-")
    return slug or "chat-agent"
