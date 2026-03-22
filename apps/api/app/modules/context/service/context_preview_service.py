from __future__ import annotations

import json
from typing import Any
import uuid

from jinja2.exceptions import SecurityError, UndefinedError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry.schemas.config_schemas import ContextInjectionItem, ModelConfig, NodeConfig
from app.modules.context.engine import ContextBuilder
from app.modules.context.engine.contracts import AUTO_INJECT_TYPES, VARIABLE_TO_INJECT_TYPE
from app.modules.project.models import Project
from app.modules.workflow.models import WorkflowExecution
from app.modules.workflow.service.snapshot_support import (
    load_skill_snapshot,
    load_workflow_snapshot,
    resolve_node_config,
)
from app.shared.runtime import SkillTemplateRenderer
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError, NotFoundError

from .dto import ContextPreviewDTO, ContextPreviewRequestDTO

CHAPTER_NUMBER_REQUIRED_TYPES = frozenset({"chapter_task", "previous_chapters", "chapter_summary"})


class ContextPreviewService:
    def __init__(
        self,
        *,
        context_builder: ContextBuilder,
        template_renderer: SkillTemplateRenderer,
    ) -> None:
        self.context_builder = context_builder
        self.template_renderer = template_renderer

    async def preview_workflow_context(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        payload: ContextPreviewRequestDTO,
        *,
        owner_id: uuid.UUID,
    ) -> ContextPreviewDTO:
        workflow = await self._require_owned_workflow(db, workflow_id, owner_id=owner_id)
        workflow_config = load_workflow_snapshot(workflow.workflow_snapshot or {})
        node = resolve_node_config(workflow_config, payload.node_id)
        if node.node_type != "generate":
            raise BusinessRuleError(f"节点不支持上下文预览: {node.id}")
        skill = load_skill_snapshot(workflow.skills_snapshot or {}, node.skill)
        model = self._resolve_model(workflow_config.model, node, skill.model)
        declared = skill.variables or skill.inputs
        rules = self._merge_rules(workflow_config, node, declared, payload.extra_inject)
        self._ensure_chapter_number_if_needed(rules, payload, node)
        referenced = self.template_renderer.referenced_variables(skill.prompt)
        context_variables, context_report = await self.context_builder.build_context(
            workflow.project_id,
            rules,
            db,
            chapter_number=payload.chapter_number,
            workflow_execution_id=workflow.id,
            model=model.name or "default",
            budget_limit=workflow_config.budget.max_tokens_per_node,
            referenced_variables=referenced,
        )
        variables = {
            **await self._project_setting_variables(db, workflow.project_id, declared),
            **context_variables,
        }
        rendered_prompt = self._render_prompt(skill.prompt, variables)
        return ContextPreviewDTO(
            workflow_execution_id=workflow.id,
            project_id=workflow.project_id,
            node_id=node.id,
            node_name=node.name,
            skill_id=skill.id,
            model_name=model.name or "",
            chapter_number=payload.chapter_number,
            referenced_variables=sorted(referenced),
            variables=variables,
            rendered_prompt=rendered_prompt,
            context_report=context_report,
        )

    def _render_prompt(self, prompt_template: str, variables: dict[str, str]) -> str:
        try:
            return self.template_renderer.render(prompt_template, variables)
        except (SecurityError, UndefinedError) as exc:
            raise ConfigurationError(f"Context preview prompt render failed: {exc}") from exc

    async def _require_owned_workflow(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
    ) -> WorkflowExecution:
        workflow = await db.scalar(
            select(WorkflowExecution)
            .join(Project, WorkflowExecution.project_id == Project.id)
            .where(
                WorkflowExecution.id == workflow_id,
                Project.owner_id == owner_id,
            )
        )
        if workflow is None:
            raise NotFoundError(f"Workflow execution not found: {workflow_id}")
        return workflow

    def _merge_rules(
        self,
        workflow_config,
        node: NodeConfig,
        declared: dict[str, Any],
        extra_inject: list[ContextInjectionItem],
    ) -> list[ContextInjectionItem]:
        config = workflow_config.context_injection
        global_rules = config.default_inject if config else []
        pattern_rules = config.rules if config else []
        merged = self.context_builder.merge_rules(
            global_rules,
            pattern_rules,
            node.id,
            node.context_injection,
        )
        if extra_inject:
            merged = self.context_builder.merge_rules(
                merged,
                [],
                node.id,
                extra_inject,
            )
        existing = {item.inject_type for item in merged}
        for name, schema in declared.items():
            inject_type = VARIABLE_TO_INJECT_TYPE.get(name)
            if (
                inject_type is None
                or inject_type in existing
                or inject_type not in AUTO_INJECT_TYPES
            ):
                continue
            merged.append(
                ContextInjectionItem.model_validate(
                    {"type": inject_type, "required": bool(getattr(schema, "required", False))}
                )
            )
        return merged

    def _ensure_chapter_number_if_needed(
        self,
        rules: list[ContextInjectionItem],
        payload: ContextPreviewRequestDTO,
        node: NodeConfig,
    ) -> None:
        needs_chapter_number = any(
            item.inject_type in CHAPTER_NUMBER_REQUIRED_TYPES for item in rules
        )
        if needs_chapter_number and payload.chapter_number is None:
            raise BusinessRuleError(f"节点上下文预览需要 chapter_number: {node.id}")

    async def _project_setting_variables(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        declared: dict[str, Any],
    ) -> dict[str, str]:
        project = await db.get(Project, project_id)
        setting = project.project_setting if project and project.project_setting else {}
        return {
            name: self._stringify_value(setting.get(name))
            for name in declared
            if name not in VARIABLE_TO_INJECT_TYPE and name in setting
        }

    def _resolve_model(
        self,
        workflow_model: ModelConfig | None,
        node: NodeConfig,
        skill_model: ModelConfig | None,
    ) -> ModelConfig:
        model = node.model or skill_model or workflow_model
        if model is None or not model.name or not model.provider:
            raise ConfigurationError(f"Node {node.id} is missing executable model configuration")
        return model

    def _stringify_value(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
