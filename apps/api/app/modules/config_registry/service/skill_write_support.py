from __future__ import annotations

from typing import Any

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.schemas import ModelConfig, SchemaField, SkillConfig
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError, NotFoundError

from .query_dto import SkillConfigUpdateDTO


def build_skill_config(payload: SkillConfigUpdateDTO) -> SkillConfig:
    return SkillConfig.model_validate(payload.model_dump(by_alias=True))


def ensure_matching_skill_id(path_skill_id: str, payload_skill_id: str) -> None:
    if payload_skill_id != path_skill_id:
        raise BusinessRuleError(
            f"Skill payload id '{payload_skill_id}' does not match path '{path_skill_id}'"
        )


def require_skill(config_loader: ConfigLoader, skill_id: str) -> SkillConfig:
    try:
        return config_loader.load_skill(skill_id)
    except ConfigurationError as exc:
        if str(exc) == f"Skill not found: {skill_id}":
            raise NotFoundError(str(exc)) from exc
        raise


def serialize_skill_document(skill: SkillConfig) -> dict[str, Any]:
    document = {
        "id": skill.id,
        "name": skill.name,
        "version": skill.version,
        "category": skill.category,
        "prompt": skill.prompt,
    }
    if skill.description is not None:
        document["description"] = skill.description
    if skill.author is not None:
        document["author"] = skill.author
    if skill.tags:
        document["tags"] = list(skill.tags)
    if skill.variables:
        document["variables"] = _dump_fields(skill.variables)
    if skill.inputs:
        document["inputs"] = _dump_fields(skill.inputs)
    if skill.outputs:
        document["outputs"] = _dump_fields(skill.outputs)
    if skill.model is not None:
        document["model"] = _dump_model(skill.model)
    return document


def _dump_fields(fields: dict[str, SchemaField]) -> dict[str, dict[str, Any]]:
    return {
        key: field.model_dump(
            by_alias=True,
            exclude_defaults=True,
            exclude_none=True,
        )
        for key, field in fields.items()
    }


def _dump_model(model: ModelConfig) -> dict[str, Any]:
    return model.model_dump(
        exclude_defaults=True,
        exclude_none=True,
    )
