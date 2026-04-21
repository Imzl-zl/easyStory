from __future__ import annotations

from typing import Any, Protocol

from app.modules.config_registry.schemas import ModelConfig
from app.shared.runtime.template_renderer import SkillTemplateRenderer
from app.shared.runtime.errors import ConfigurationError

from ..agents.assistant_agent_service import AssistantAgentService
from ..assistant_execution_support import (
    build_hook_agent_variables,
    hook_agent_response_format,
    require_agent_skill,
    resolve_hook_agent_model,
    resolve_hook_agent_output,
)
from ..preferences.preferences_service import AssistantPreferencesService
from ..rules.assistant_rule_service import AssistantRuleService
from ..rules.assistant_rule_support import build_assistant_system_prompt
from ..skills.assistant_skill_service import AssistantSkillService
from .assistant_hook_support import AssistantHookExecutionContext


class AssistantHookAgentLlmCaller(Protocol):
    async def __call__(
        self,
        db,
        *,
        prompt: str,
        system_prompt: str | None,
        model: ModelConfig,
        owner_id,
        project_id,
        response_format: str | None = None,
    ) -> dict[str, Any]: ...


class AssistantHookAgentRuntime(Protocol):
    async def run(
        self,
        context: AssistantHookExecutionContext,
        *,
        agent_id: str,
        input_mapping: dict[str, str],
    ) -> Any: ...


class AssistantHookAgentRuntimeImpl:
    def __init__(
        self,
        *,
        assistant_agent_service: AssistantAgentService,
        assistant_skill_service: AssistantSkillService,
        assistant_preferences_service: AssistantPreferencesService,
        assistant_rule_service: AssistantRuleService,
        template_renderer: SkillTemplateRenderer,
        llm_caller: AssistantHookAgentLlmCaller,
    ) -> None:
        self.assistant_agent_service = assistant_agent_service
        self.assistant_skill_service = assistant_skill_service
        self.assistant_preferences_service = assistant_preferences_service
        self.assistant_rule_service = assistant_rule_service
        self.template_renderer = template_renderer
        self.llm_caller = llm_caller

    async def run(
        self,
        context: AssistantHookExecutionContext,
        *,
        agent_id: str,
        input_mapping: dict[str, str],
    ) -> Any:
        agent = self.assistant_agent_service.resolve_agent(
            agent_id,
            owner_id=context.owner_id,
            allow_disabled=True,
        )
        skill = require_agent_skill(
            lambda skill_id: self.assistant_skill_service.resolve_skill(
                skill_id,
                owner_id=context.owner_id,
                project_id=context.project_id,
                allow_disabled=True,
            ),
            agent,
        )
        variables = build_hook_agent_variables(context, input_mapping)
        prompt = self.template_renderer.render(skill.prompt, variables)
        preferences = await self.assistant_preferences_service.resolve_preferences(
            context.db,
            owner_id=context.owner_id,
            project_id=context.project_id,
        )
        model = resolve_hook_agent_model(
            agent=agent,
            skill=skill,
            preferences=preferences,
            assistant_model=context.assistant_model,
        )
        rule_bundle = await self.assistant_rule_service.build_rule_bundle(
            context.db,
            owner_id=context.owner_id,
            project_id=context.project_id,
        )
        system_prompt = build_assistant_system_prompt(
            agent.system_prompt,
            user_content=rule_bundle.user_content,
            project_content=rule_bundle.project_content,
        )
        raw_output = await self.llm_caller(
            context.db,
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            owner_id=context.owner_id,
            project_id=context.project_id,
            response_format=hook_agent_response_format(agent),
        )
        result = resolve_hook_agent_output(agent, raw_output.get("content"))
        if result is None:
            raise ConfigurationError("Assistant hook agent runtime completed without result")
        return result


LangGraphAssistantHookAgentRuntime = AssistantHookAgentRuntimeImpl
