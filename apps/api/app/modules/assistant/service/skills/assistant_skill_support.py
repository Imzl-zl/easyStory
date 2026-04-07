from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import re
import secrets

import yaml

from app.modules.config_registry.infrastructure.skill_input_validator import validate_input_schema
from app.modules.config_registry.schemas import ModelConfig, SchemaField, SkillConfig
from app.shared.runtime import SkillTemplateRenderer
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError

from ..context.assistant_prompt_support import (
    CONVERSATION_HISTORY_VARIABLE,
    USER_INPUT_VARIABLE,
)
from .assistant_skill_dto import (
    AssistantSkillCreateDTO,
    AssistantSkillDetailDTO,
    AssistantSkillSummaryDTO,
    AssistantSkillUpdateDTO,
    normalize_assistant_skill_name,
)
from ..preferences.preferences_support import normalize_optional_text

FRONTMATTER_BOUNDARY = "---"
SKILL_FILE_NAME = "SKILL.md"
SKILLS_DIR_NAME = "skills"
USER_SKILL_AUTHOR = "user"
USER_SKILL_CATEGORY = "assistant"
USER_SKILL_ID_PREFIX = "skill.user."
PROJECT_SKILL_ID_PREFIX = "skill.project."
SKILL_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
SLUG_PATTERN = re.compile(r"[^a-z0-9]+")

@dataclass(frozen=True)
class StoredAssistantSkill:
    id: str
    name: str
    description: str | None
    enabled: bool
    content: str
    default_provider: str | None
    default_model_name: str | None
    default_max_output_tokens: int | None
    updated_at: datetime | None
    path: Path

def build_skill_summary(record: StoredAssistantSkill) -> AssistantSkillSummaryDTO:
    return AssistantSkillSummaryDTO(
        id=record.id,
        file_name=record.path.name,
        name=record.name,
        description=record.description,
        enabled=record.enabled,
        updated_at=record.updated_at,
    )

def build_skill_detail(record: StoredAssistantSkill) -> AssistantSkillDetailDTO:
    return AssistantSkillDetailDTO(
        id=record.id,
        file_name=record.path.name,
        name=record.name,
        description=record.description,
        enabled=record.enabled,
        content=record.content,
        default_provider=record.default_provider,
        default_model_name=record.default_model_name,
        default_max_output_tokens=record.default_max_output_tokens,
        updated_at=record.updated_at,
    )

def build_runtime_skill(record: StoredAssistantSkill) -> SkillConfig:
    skill = SkillConfig(
        id=record.id,
        name=record.name,
        description=record.description,
        category=USER_SKILL_CATEGORY,
        author=USER_SKILL_AUTHOR,
        prompt=record.content,
        variables={
            CONVERSATION_HISTORY_VARIABLE: SchemaField(
                type="string",
                required=False,
                default="",
                description="前面的聊天记录",
            ),
            USER_INPUT_VARIABLE: SchemaField(
                type="string",
                required=True,
                description="用户最新输入",
            ),
        },
        model=build_skill_model(record),
    )
    validate_runtime_skill(skill)
    return skill

def build_user_skill_path(root: Path, user_id, skill_id: str) -> Path:
    validate_skill_id(skill_id)
    return root / "users" / str(user_id) / SKILLS_DIR_NAME / skill_id / SKILL_FILE_NAME


def build_project_skill_path(root: Path, project_id, skill_id: str) -> Path:
    validate_skill_id(skill_id)
    return root / "projects" / str(project_id) / SKILLS_DIR_NAME / skill_id / SKILL_FILE_NAME


def build_skill_path(root: Path, user_id, skill_id: str) -> Path:
    return build_user_skill_path(root, user_id, skill_id)


def detail_to_record(
    detail: AssistantSkillDetailDTO,
    *,
    path: Path,
    updated_at: datetime | None = None,
) -> StoredAssistantSkill:
    return StoredAssistantSkill(
        id=detail.id,
        name=detail.name,
        description=detail.description,
        enabled=detail.enabled,
        content=detail.content,
        default_provider=detail.default_provider,
        default_model_name=detail.default_model_name,
        default_max_output_tokens=detail.default_max_output_tokens,
        updated_at=updated_at,
        path=path,
    )


def create_user_skill_detail(
    payload: AssistantSkillCreateDTO,
    *,
    existing_ids: set[str],
) -> AssistantSkillDetailDTO:
    return _create_skill_detail(
        payload,
        skill_id=create_user_skill_id(payload.name, existing_ids=existing_ids),
    )


def create_project_skill_detail(
    payload: AssistantSkillCreateDTO,
    *,
    existing_ids: set[str],
) -> AssistantSkillDetailDTO:
    return _create_skill_detail(
        payload,
        skill_id=create_project_skill_id(payload.name, existing_ids=existing_ids),
    )


def _create_skill_detail(
    payload: AssistantSkillCreateDTO,
    *,
    skill_id: str,
) -> AssistantSkillDetailDTO:
    return AssistantSkillDetailDTO(
        id=skill_id,
        name=payload.name,
        description=normalize_optional_text(payload.description),
        enabled=payload.enabled,
        content=normalize_skill_content(payload.content),
        default_provider=normalize_optional_text(payload.default_provider),
        default_model_name=normalize_optional_text(payload.default_model_name),
        default_max_output_tokens=payload.default_max_output_tokens,
        updated_at=None,
    )


def update_skill_detail(
    skill_id: str,
    payload: AssistantSkillUpdateDTO,
    *,
    updated_at: datetime | None,
) -> AssistantSkillDetailDTO:
    return AssistantSkillDetailDTO(
        id=skill_id,
        name=payload.name,
        description=normalize_optional_text(payload.description),
        enabled=payload.enabled,
        content=normalize_skill_content(payload.content),
        default_provider=normalize_optional_text(payload.default_provider),
        default_model_name=normalize_optional_text(payload.default_model_name),
        default_max_output_tokens=payload.default_max_output_tokens,
        updated_at=updated_at,
    )


def format_skill_markdown(detail: AssistantSkillDetailDTO) -> str:
    metadata = {
        "id": detail.id,
        "name": detail.name,
        "enabled": detail.enabled,
    }
    if detail.description is not None:
        metadata["description"] = detail.description
    model = dump_skill_model(detail)
    if model:
        metadata["model"] = model
    metadata_text = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).strip()
    return (
        f"{FRONTMATTER_BOUNDARY}\n{metadata_text}\n{FRONTMATTER_BOUNDARY}\n\n"
        f"{normalize_skill_content(detail.content)}\n"
    )


def parse_skill_markdown(path: Path, raw_text: str) -> StoredAssistantSkill:
    metadata, content = split_frontmatter(raw_text, path)
    skill_id = metadata.get("id")
    name = metadata.get("name")
    if not isinstance(skill_id, str) or not skill_id.strip():
        raise ConfigurationError(f"Assistant skill file is missing id: {path}")
    if not isinstance(name, str) or not name.strip():
        raise ConfigurationError(f"Assistant skill file is missing name: {path}")
    validate_skill_id(skill_id.strip())
    model = metadata.get("model")
    provider, model_name, max_output_tokens = parse_skill_model(model, path)
    enabled = metadata.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ConfigurationError(f"Assistant skill field 'enabled' must be a boolean: {path}")
    return StoredAssistantSkill(
        id=skill_id.strip(),
        name=normalize_assistant_skill_name(name),
        description=normalize_optional_text(read_optional_string(metadata, "description", path)),
        enabled=enabled,
        content=normalize_skill_content(content),
        default_provider=provider,
        default_model_name=model_name,
        default_max_output_tokens=max_output_tokens,
        updated_at=datetime.fromtimestamp(path.stat().st_mtime, tz=UTC),
        path=path,
    )


def validate_runtime_skill(skill: SkillConfig) -> None:
    renderer = SkillTemplateRenderer()
    errors = renderer.validate(skill.prompt, set(skill.variables))
    if errors:
        raise BusinessRuleError("Skill 内容里包含未声明的变量，请只使用 {{ user_input }} 和 {{ conversation_history }}。")
    validate_input_schema(skill.variables, {USER_INPUT_VARIABLE: "hello", CONVERSATION_HISTORY_VARIABLE: ""})


def validate_skill_id(skill_id: str) -> None:
    if not SKILL_ID_PATTERN.fullmatch(skill_id):
        raise ConfigurationError(f"Assistant skill id is invalid: {skill_id}")


def create_user_skill_id(name: str, *, existing_ids: set[str]) -> str:
    base_slug = slugify_skill_name(name)
    while True:
        candidate = f"{USER_SKILL_ID_PREFIX}{base_slug}-{secrets.token_hex(3)}"
        if candidate not in existing_ids:
            return candidate


def create_project_skill_id(name: str, *, existing_ids: set[str]) -> str:
    base_slug = slugify_skill_name(name)
    while True:
        candidate = f"{PROJECT_SKILL_ID_PREFIX}{base_slug}-{secrets.token_hex(3)}"
        if candidate not in existing_ids:
            return candidate


def slugify_skill_name(name: str) -> str:
    normalized = normalize_optional_text(name.lower()) or "chat-skill"
    slug = SLUG_PATTERN.sub("-", normalized).strip("-")
    return slug or "chat-skill"


def normalize_skill_content(content: str) -> str:
    normalized = content.replace("\r\n", "\n").strip()
    if not normalized:
        raise BusinessRuleError("Skill 内容不能为空")
    return normalized


def split_frontmatter(raw_text: str, path: Path) -> tuple[dict, str]:
    normalized = raw_text.replace("\r\n", "\n")
    if not normalized.startswith(f"{FRONTMATTER_BOUNDARY}\n"):
        raise ConfigurationError(f"Assistant skill file must start with frontmatter: {path}")
    parts = normalized.split(f"\n{FRONTMATTER_BOUNDARY}\n", maxsplit=1)
    if len(parts) != 2:
        raise ConfigurationError(f"Assistant skill file frontmatter is not properly closed: {path}")
    metadata_text = parts[0].removeprefix(f"{FRONTMATTER_BOUNDARY}\n")
    metadata = yaml.safe_load(metadata_text) or {}
    if not isinstance(metadata, dict):
        raise ConfigurationError(f"Assistant skill frontmatter must be a YAML object: {path}")
    return metadata, parts[1]


def read_optional_string(metadata: dict, key: str, path: Path) -> str | None:
    value = metadata.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigurationError(f"Assistant skill field '{key}' must be a string: {path}")
    return value


def parse_skill_model(model: object, path: Path) -> tuple[str | None, str | None, int | None]:
    if model is None:
        return None, None, None
    if not isinstance(model, dict):
        raise ConfigurationError(f"Assistant skill model frontmatter must be an object: {path}")
    provider = normalize_optional_text(read_optional_string(model, "provider", path))
    model_name = normalize_optional_text(read_optional_string(model, "name", path))
    max_output_tokens = model.get("max_tokens")
    if isinstance(max_output_tokens, bool) or (
        max_output_tokens is not None and not isinstance(max_output_tokens, int)
    ):
        raise ConfigurationError(f"Assistant skill model max_tokens must be an integer: {path}")
    return provider, model_name, max_output_tokens


def build_skill_model(record: StoredAssistantSkill) -> ModelConfig | None:
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


def dump_skill_model(detail: AssistantSkillDetailDTO) -> dict[str, object]:
    payload: dict[str, object] = {}
    if detail.default_provider is not None:
        payload["provider"] = detail.default_provider
    if detail.default_model_name is not None:
        payload["name"] = detail.default_model_name
    if detail.default_max_output_tokens is not None:
        payload["max_tokens"] = detail.default_max_output_tokens
    return payload
