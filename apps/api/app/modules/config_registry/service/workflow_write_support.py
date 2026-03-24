from __future__ import annotations

from typing import Any

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.schemas import (
    BudgetConfig,
    ContextInjectionConfig,
    ContextInjectionItem,
    FixStrategy,
    LoopConfig,
    ModelConfig,
    ModelFallbackConfig,
    RetryConfig,
    ReviewConfig,
    SafetyConfig,
    WorkflowConfig,
    WorkflowSettings,
)
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError, NotFoundError

from .query_dto import WorkflowConfigUpdateDTO
from .write_validation_support import validate_config_model


def build_workflow_config(payload: WorkflowConfigUpdateDTO) -> WorkflowConfig:
    document = payload.model_dump()
    document["nodes"] = [_build_workflow_node(item) for item in document["nodes"]]
    if document["context_injection"] is not None:
        document["context_injection"] = _build_context_injection_config(document["context_injection"])
    return validate_config_model(WorkflowConfig, document)


def ensure_matching_workflow_id(path_workflow_id: str, payload_workflow_id: str) -> None:
    if payload_workflow_id != path_workflow_id:
        raise BusinessRuleError(
            f"Workflow payload id '{payload_workflow_id}' does not match path '{path_workflow_id}'"
        )


def require_workflow(config_loader: ConfigLoader, workflow_id: str) -> WorkflowConfig:
    try:
        return config_loader.load_workflow(workflow_id)
    except ConfigurationError as exc:
        if str(exc) == f"Workflow not found: {workflow_id}":
            raise NotFoundError(str(exc)) from exc
        raise


def serialize_workflow_document(workflow: WorkflowConfig) -> dict[str, Any]:
    document: dict[str, Any] = {
        "id": workflow.id,
        "name": workflow.name,
        "version": workflow.version,
        "mode": workflow.mode,
    }
    if workflow.description is not None:
        document["description"] = workflow.description
    if workflow.author is not None:
        document["author"] = workflow.author
    if workflow.tags:
        document["tags"] = list(workflow.tags)
    if workflow.changelog:
        document["changelog"] = [entry.model_dump(exclude_none=True) for entry in workflow.changelog]
    if workflow.settings != WorkflowSettings():
        document["settings"] = workflow.settings.model_dump(exclude_none=True)
    if workflow.model is not None:
        document["model"] = _dump_model(workflow.model)
    if workflow.budget != BudgetConfig():
        document["budget"] = workflow.budget.model_dump(exclude_none=True)
    if workflow.safety != SafetyConfig():
        document["safety"] = workflow.safety.model_dump(exclude_none=True)
    if workflow.retry != RetryConfig():
        document["retry"] = workflow.retry.model_dump(exclude_none=True)
    if workflow.model_fallback != ModelFallbackConfig():
        document["model_fallback"] = workflow.model_fallback.model_dump(exclude_none=True)
    if workflow.context_injection is not None:
        document["context_injection"] = _dump_context_injection_config(workflow.context_injection)
    document["nodes"] = [_dump_workflow_node(node) for node in workflow.nodes]
    return document


def _build_context_injection_config(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "enabled": document["enabled"],
        "default_inject": [_build_context_injection_item(item) for item in document["default_inject"]],
        "rules": [
            {
                "node_pattern": rule["node_pattern"],
                "inject": [_build_context_injection_item(item) for item in rule["inject"]],
            }
            for rule in document["rules"]
        ],
    }


def _build_context_injection_item(document: dict[str, Any]) -> dict[str, Any]:
    item = dict(document)
    item["type"] = item.pop("inject_type")
    return item


def _build_workflow_node(document: dict[str, Any]) -> dict[str, Any]:
    node = dict(document)
    node["type"] = node.pop("node_type")
    node["skill"] = node.pop("skill_id")
    node["reviewers"] = node.pop("reviewer_ids")
    node["fix_skill"] = node.pop("fix_skill_id")
    node["context_injection"] = [
        _build_context_injection_item(item) for item in node["context_injection"]
    ]
    return node


def _dump_context_injection_config(config: ContextInjectionConfig) -> dict[str, Any]:
    document: dict[str, Any] = {"enabled": config.enabled}
    if config.default_inject:
        document["default_inject"] = [_dump_context_injection_item(item) for item in config.default_inject]
    if config.rules:
        document["rules"] = [
            {
                "node_pattern": rule.node_pattern,
                "inject": [_dump_context_injection_item(item) for item in rule.inject],
            }
            for rule in config.rules
        ]
    return document


def _dump_context_injection_item(item: ContextInjectionItem) -> dict[str, Any]:
    document: dict[str, Any] = {"type": item.inject_type, "required": item.required}
    if item.count is not None:
        document["count"] = item.count
    if item.analysis_id is not None:
        document["analysis_id"] = item.analysis_id
    if item.inject_fields:
        document["inject_fields"] = list(item.inject_fields)
    return document


def _dump_model(model: ModelConfig) -> dict[str, Any]:
    return model.model_dump(exclude_defaults=True, exclude_none=True)


def _dump_workflow_node(node) -> dict[str, Any]:
    document: dict[str, Any] = {
        "id": node.id,
        "name": node.name,
        "type": node.node_type,
    }
    if node.skill is not None:
        document["skill"] = node.skill
    if node.depends_on:
        document["depends_on"] = list(node.depends_on)
    if node.hooks:
        document["hooks"] = {stage: list(hook_ids) for stage, hook_ids in node.hooks.items()}
    if node.reviewers:
        document["reviewers"] = list(node.reviewers)
    if node.auto_proceed is not None:
        document["auto_proceed"] = node.auto_proceed
    if node.auto_review is not None:
        document["auto_review"] = node.auto_review
    if node.auto_fix is not None:
        document["auto_fix"] = node.auto_fix
    if node.review_mode != "serial":
        document["review_mode"] = node.review_mode
    if node.max_concurrent_reviewers != 3:
        document["max_concurrent_reviewers"] = node.max_concurrent_reviewers
    if node.review_config != ReviewConfig():
        document["review_config"] = node.review_config.model_dump(exclude_none=True)
    if node.max_fix_attempts is not None:
        document["max_fix_attempts"] = node.max_fix_attempts
    if node.on_fix_fail != "pause":
        document["on_fix_fail"] = node.on_fix_fail
    if node.fix_skill is not None:
        document["fix_skill"] = node.fix_skill
    if node.fix_strategy != FixStrategy():
        document["fix_strategy"] = node.fix_strategy.model_dump(exclude_none=True)
    if node.loop != LoopConfig():
        document["loop"] = node.loop.model_dump(exclude_none=True)
    if node.model is not None:
        document["model"] = _dump_model(node.model)
    if node.context_injection:
        document["context_injection"] = [_dump_context_injection_item(item) for item in node.context_injection]
    if node.input_mapping:
        document["input_mapping"] = dict(node.input_mapping)
    if node.formats:
        document["formats"] = list(node.formats)
    return document
