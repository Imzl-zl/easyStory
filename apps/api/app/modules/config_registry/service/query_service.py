from __future__ import annotations

from app.modules.config_registry import ConfigLoader

from .agent_write_support import require_agent
from .hook_write_support import require_hook
from .query_dto import (
    AgentConfigDetailDTO,
    AgentConfigSummaryDTO,
    HookConfigDetailDTO,
    HookConfigSummaryDTO,
    SkillConfigDetailDTO,
    SkillConfigSummaryDTO,
    WorkflowConfigDetailDTO,
    WorkflowConfigSummaryDTO,
)
from .query_support import (
    to_agent_detail,
    to_agent_summary,
    to_hook_detail,
    to_hook_summary,
    to_skill_detail,
    to_skill_summary,
)
from .workflow_query_support import (
    to_workflow_detail,
    to_workflow_summary,
)
from .skill_write_support import require_skill
from .workflow_write_support import require_workflow


class ConfigRegistryQueryService:
    def __init__(self, config_loader: ConfigLoader) -> None:
        self.config_loader = config_loader

    async def list_skills(self) -> list[SkillConfigSummaryDTO]:
        skills = sorted(self.config_loader.list_skills(), key=lambda item: (item.category, item.name, item.id))
        return [to_skill_summary(skill) for skill in skills]

    async def get_skill(self, skill_id: str) -> SkillConfigDetailDTO:
        return to_skill_detail(require_skill(self.config_loader, skill_id))

    async def list_agents(self) -> list[AgentConfigSummaryDTO]:
        agents = sorted(
            self.config_loader.list_agents(),
            key=lambda item: (item.agent_type, item.name, item.id),
        )
        return [to_agent_summary(agent) for agent in agents]

    async def get_agent(self, agent_id: str) -> AgentConfigDetailDTO:
        return to_agent_detail(require_agent(self.config_loader, agent_id))

    async def list_hooks(self) -> list[HookConfigSummaryDTO]:
        hooks = sorted(
            self.config_loader.list_hooks(),
            key=lambda item: (-item.priority, item.name, item.id),
        )
        return [to_hook_summary(hook) for hook in hooks]

    async def get_hook(self, hook_id: str) -> HookConfigDetailDTO:
        return to_hook_detail(require_hook(self.config_loader, hook_id))

    async def list_workflows(self) -> list[WorkflowConfigSummaryDTO]:
        workflows = sorted(self.config_loader.list_workflows(), key=lambda item: (item.name, item.id))
        return [to_workflow_summary(workflow) for workflow in workflows]

    async def get_workflow(self, workflow_id: str) -> WorkflowConfigDetailDTO:
        return to_workflow_detail(require_workflow(self.config_loader, workflow_id))
