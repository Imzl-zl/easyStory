import logging
from pathlib import Path

import yaml

from app.schemas.config_schemas import (
    AgentConfig,
    HookConfig,
    SkillConfig,
    WorkflowConfig,
)

logger = logging.getLogger(__name__)


class ConfigLoader:
    def __init__(self, config_root: Path):
        self.config_root = config_root
        self._skills: dict[str, SkillConfig] = {}
        self._agents: dict[str, AgentConfig] = {}
        self._hooks: dict[str, HookConfig] = {}
        self._workflows: dict[str, WorkflowConfig] = {}
        self._load_all()

    def _load_all(self) -> None:
        self._load_dir("skills", "skill", SkillConfig, self._skills)
        self._load_dir("agents", "agent", AgentConfig, self._agents)
        self._load_dir("hooks", "hook", HookConfig, self._hooks)
        self._load_dir("workflows", "workflow", WorkflowConfig, self._workflows)

    def _load_dir(
        self,
        subdir: str,
        root_key: str,
        model_cls: type,
        cache: dict,
    ) -> None:
        target = self.config_root / subdir
        if not target.exists():
            return
        for yaml_file in target.rglob("*.yaml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if not data or root_key not in data:
                    logger.warning("Skipping %s: missing '%s' key", yaml_file, root_key)
                    continue
                config = model_cls(**data[root_key])
                cache[config.id] = config
            except Exception:
                logger.exception("Failed to load config from %s", yaml_file)

    def load_skill(self, skill_id: str) -> SkillConfig:
        if skill_id not in self._skills:
            raise ValueError(f"Skill not found: {skill_id}")
        return self._skills[skill_id]

    def load_agent(self, agent_id: str) -> AgentConfig:
        if agent_id not in self._agents:
            raise ValueError(f"Agent not found: {agent_id}")
        return self._agents[agent_id]

    def load_hook(self, hook_id: str) -> HookConfig:
        if hook_id not in self._hooks:
            raise ValueError(f"Hook not found: {hook_id}")
        return self._hooks[hook_id]

    def load_workflow(self, workflow_id: str) -> WorkflowConfig:
        if workflow_id not in self._workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        return self._workflows[workflow_id]

    def validate_skill_input(self, skill: SkillConfig, input_data: dict) -> bool:
        for var_name, var_config in skill.variables.items():
            if var_config.required and var_name not in input_data:
                raise ValueError(f"Required variable missing: {var_name}")
        return True

    def list_skills(self) -> list[SkillConfig]:
        return list(self._skills.values())

    def list_agents(self) -> list[AgentConfig]:
        return list(self._agents.values())

    def list_hooks(self) -> list[HookConfig]:
        return list(self._hooks.values())

    def list_workflows(self) -> list[WorkflowConfig]:
        return list(self._workflows.values())
