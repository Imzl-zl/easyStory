from __future__ import annotations

from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry.schemas.config_schemas import (
    ContextInjectionItem,
    ModelConfig,
    NodeConfig,
    SkillConfig,
    WorkflowConfig,
)
from app.modules.context.engine.contracts import AUTO_INJECT_TYPES, VARIABLE_TO_INJECT_TYPE
from app.modules.project.models import Project
from app.modules.workflow.models import WorkflowExecution
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError

from .snapshot_support import load_skill_snapshot


class WorkflowRuntimePromptMixin:
    async def _build_prompt_bundle(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        *,
        chapter_number: int | None,
    ) -> dict[str, Any]:
        skill = load_skill_snapshot(workflow.skills_snapshot or {}, node.skill)
        model = self._resolve_model(workflow_config, node, skill)
        prompt_variables, context_report = await self._resolve_prompt_variables(
            db,
            workflow,
            workflow_config,
            node,
            skill,
            model,
            chapter_number=chapter_number,
        )
        prompt = self.template_renderer.render(skill.prompt, prompt_variables)
        return {
            "prompt": prompt,
            "system_prompt": None,
            "model": model,
            "response_format": "json_object" if node.id == "chapter_split" else "text",
            "context_snapshot_hash": self._hash_payload(prompt_variables),
            "input_data": {
                "skill_id": skill.id,
                "model_name": model.name,
                "provider": model.provider,
                "prompt": prompt,
                "context_report": context_report,
            },
        }

    async def _resolve_prompt_variables(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        skill: SkillConfig,
        model: ModelConfig,
        *,
        chapter_number: int | None,
    ) -> tuple[dict[str, str], dict[str, Any]]:
        declared = skill.variables or skill.inputs
        rules = self._merge_rules(workflow_config, node, declared)
        referenced = self.template_renderer.referenced_variables(skill.prompt)
        context_variables, context_report = await self.context_builder.build_context(
            workflow.project_id,
            rules,
            db,
            chapter_number=chapter_number,
            workflow_execution_id=workflow.id,
            model=model.name or "default",
            budget_limit=workflow_config.budget.max_tokens_per_node,
            referenced_variables=referenced,
        )
        prompt_variables = {
            **(await self._project_setting_variables(db, workflow.project_id, declared)),
            **context_variables,
        }
        missing = [
            name
            for name, schema in declared.items()
            if getattr(schema, "required", False) and not prompt_variables.get(name)
        ]
        if missing:
            raise BusinessRuleError(f"缺少 Skill 必填变量: {', '.join(sorted(missing))}")
        return prompt_variables, context_report

    def _merge_rules(
        self,
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        declared: dict[str, Any],
    ) -> list[ContextInjectionItem]:
        config = workflow_config.context_injection
        global_rules = config.default_inject if config else []
        pattern_rules = config.rules if config else []
        merged = self.context_builder.merge_rules(global_rules, pattern_rules, node.id, node.context_injection)
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
        workflow_config: WorkflowConfig,
        node: NodeConfig,
        skill: SkillConfig,
    ) -> ModelConfig:
        model = node.model or skill.model or workflow_config.model
        if model is None or not model.name or not model.provider:
            raise ConfigurationError(f"Node {node.id} is missing executable model configuration")
        return model
