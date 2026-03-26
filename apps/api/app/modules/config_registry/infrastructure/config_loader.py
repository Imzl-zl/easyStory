from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import yaml

from app.modules.config_registry.infrastructure.skill_input_validator import (
    SkillInputValidationError,
    validate_input_schema,
)
from app.modules.config_registry.schemas.config_schemas import (
    AgentConfig,
    HookConfig,
    McpServerConfig,
    SkillConfig,
    WorkflowConfig,
)
from app.modules.config_registry.schemas.hook_schema import expected_workflow_node_hook_stage
from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.template_renderer import SkillTemplateRenderer

ConfigModel = TypeVar(
    "ConfigModel",
    SkillConfig,
    AgentConfig,
    HookConfig,
    WorkflowConfig,
    McpServerConfig,
)


class ConfigLoader:
    def __init__(self, config_root: Path):
        self.config_root = config_root
        self._template_renderer = SkillTemplateRenderer()
        self._skills: dict[str, SkillConfig] = {}
        self._agents: dict[str, AgentConfig] = {}
        self._hooks: dict[str, HookConfig] = {}
        self._mcp_servers: dict[str, McpServerConfig] = {}
        self._workflows: dict[str, WorkflowConfig] = {}
        self._sources: dict[str, Path] = {}
        self._load_all()

    def reload(self) -> None:
        self._skills = {}
        self._agents = {}
        self._hooks = {}
        self._mcp_servers = {}
        self._workflows = {}
        self._sources = {}
        self._load_all()

    def _load_all(self) -> None:
        self._skills = self._load_dir("skills", "skill", SkillConfig)
        self._agents = self._load_dir("agents", "agent", AgentConfig)
        self._hooks = self._load_dir("hooks", "hook", HookConfig)
        self._mcp_servers = self._load_dir("mcp_servers", "mcp_server", McpServerConfig)
        self._workflows = self._load_dir("workflows", "workflow", WorkflowConfig)
        self._validate_references()

    def _load_dir(
        self,
        subdir: str,
        root_key: str,
        model_cls: type[ConfigModel],
    ) -> dict[str, ConfigModel]:
        target = self.config_root / subdir
        if not target.exists():
            return {}
        loaded: dict[str, ConfigModel] = {}
        for yaml_file in sorted(target.rglob("*.yaml")):
            payload = self._read_yaml(yaml_file, root_key)
            try:
                config = model_cls.model_validate(payload)
            except Exception as exc:
                raise ConfigurationError(
                    f"Invalid {root_key} config in {yaml_file}: {exc}"
                ) from exc
            self._register(loaded, config.id, config, yaml_file)
        return loaded

    def _read_yaml(self, yaml_file: Path, root_key: str) -> dict:
        with yaml_file.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        if not data:
            raise ConfigurationError(f"Invalid YAML: {yaml_file} is empty")
        if root_key not in data:
            raise ConfigurationError(f"Invalid YAML: {yaml_file} missing '{root_key}' root key")
        return data[root_key]

    def _register(self, cache: dict, config_id: str, config: ConfigModel, yaml_file: Path) -> None:
        if config_id in self._sources:
            previous = self._sources[config_id]
            raise ConfigurationError(
                f"Duplicate config id '{config_id}' in {previous} and {yaml_file}"
            )
        cache[config_id] = config
        self._sources[config_id] = yaml_file

    def _validate_references(self) -> None:
        self._validate_skill_templates()
        self._validate_agent_refs()
        self._validate_hook_refs()
        self._validate_workflow_refs()

    def _validate_skill_templates(self) -> None:
        for skill in self._skills.values():
            declared = set(skill.inputs or skill.variables)
            errors = self._template_renderer.validate(skill.prompt, declared)
            if errors:
                message = "; ".join(errors)
                raise ConfigurationError(f"skill {skill.id} template is invalid: {message}")

    def _validate_agent_refs(self) -> None:
        for agent in self._agents.values():
            for skill_id in agent.skills:
                self._require(self._skills, skill_id, f"agent {agent.id} skill")
            for server_id in agent.mcp_servers:
                self._require(self._mcp_servers, server_id, f"agent {agent.id} mcp_server")

    def _validate_hook_refs(self) -> None:
        for hook in self._hooks.values():
            if hook.action.action_type == "agent":
                agent_id = hook.action.config.get("agent_id")
                if not agent_id:
                    raise ConfigurationError(f"hook {hook.id} agent action missing agent_id")
                self._require(self._agents, agent_id, f"hook {hook.id} action agent")
            if hook.action.action_type == "mcp":
                server_id = hook.action.config.get("server_id")
                if not server_id:
                    raise ConfigurationError(f"hook {hook.id} mcp action missing server_id")
                self._require(self._mcp_servers, server_id, f"hook {hook.id} action mcp_server")

    def _validate_workflow_refs(self) -> None:
        for workflow in self._workflows.values():
            default_fix_skill = workflow.settings.default_fix_skill
            if default_fix_skill:
                self._require(self._skills, default_fix_skill, f"workflow {workflow.id} default_fix_skill")
            for node in workflow.nodes:
                if node.skill:
                    self._require(self._skills, node.skill, f"workflow {workflow.id} node {node.id} skill")
                if node.fix_skill:
                    self._require(
                        self._skills,
                        node.fix_skill,
                        f"workflow {workflow.id} node {node.id} fix_skill",
                    )
                for reviewer in node.reviewers:
                    self._require(
                        self._agents,
                        reviewer,
                        f"workflow {workflow.id} node {node.id} reviewer",
                    )
                for stage, hook_ids in node.hooks.items():
                    if stage not in {"before", "after"}:
                        raise ConfigurationError(
                            f"workflow {workflow.id} node {node.id} has invalid hook stage '{stage}'"
                        )
                    for hook_id in hook_ids:
                        hook = self._require(
                            self._hooks,
                            hook_id,
                            f"workflow {workflow.id} node {node.id} hook",
                        )
                        self._validate_workflow_node_hook(workflow.id, node.id, stage, hook)

    def _validate_workflow_node_hook(
        self,
        workflow_id: str,
        node_id: str,
        stage: str,
        hook: HookConfig,
    ) -> None:
        expected_stage = expected_workflow_node_hook_stage(hook.trigger.event)
        if expected_stage is None:
            raise ConfigurationError(
                f"workflow {workflow_id} node {node_id} hook '{hook.id}' event "
                f"'{hook.trigger.event}' is not supported on workflow nodes"
            )
        if expected_stage != stage:
            raise ConfigurationError(
                f"workflow {workflow_id} node {node_id} hook '{hook.id}' event "
                f"'{hook.trigger.event}' must use stage '{expected_stage}', got '{stage}'"
            )

    def _require(self, cache: dict[str, ConfigModel], config_id: str, context: str) -> ConfigModel:
        if config_id not in cache:
            raise ConfigurationError(f"{context} references missing config '{config_id}'")
        return cache[config_id]

    def load_skill(self, skill_id: str) -> SkillConfig:
        return self._get(self._skills, skill_id, "Skill")

    def load_agent(self, agent_id: str) -> AgentConfig:
        return self._get(self._agents, agent_id, "Agent")

    def load_hook(self, hook_id: str) -> HookConfig:
        return self._get(self._hooks, hook_id, "Hook")

    def load_workflow(self, workflow_id: str) -> WorkflowConfig:
        return self._get(self._workflows, workflow_id, "Workflow")

    def load_mcp_server(self, server_id: str) -> McpServerConfig:
        return self._get(self._mcp_servers, server_id, "MCP server")

    def get_source_path(self, config_id: str) -> Path:
        if config_id not in self._sources:
            raise ConfigurationError(f"Config source not found: {config_id}")
        return self._sources[config_id]

    def _get(self, cache: dict[str, ConfigModel], config_id: str, label: str) -> ConfigModel:
        if config_id not in cache:
            raise ConfigurationError(f"{label} not found: {config_id}")
        return cache[config_id]

    def validate_skill_input(self, skill: SkillConfig, input_data: dict) -> bool:
        declared = skill.inputs or skill.variables
        try:
            validate_input_schema(declared, input_data)
        except SkillInputValidationError as exc:
            raise ConfigurationError(str(exc)) from exc
        return True

    def list_skills(self) -> list[SkillConfig]:
        return list(self._skills.values())

    def list_agents(self) -> list[AgentConfig]:
        return list(self._agents.values())

    def list_hooks(self) -> list[HookConfig]:
        return list(self._hooks.values())

    def list_workflows(self) -> list[WorkflowConfig]:
        return list(self._workflows.values())

    def list_mcp_servers(self) -> list[McpServerConfig]:
        return list(self._mcp_servers.values())
