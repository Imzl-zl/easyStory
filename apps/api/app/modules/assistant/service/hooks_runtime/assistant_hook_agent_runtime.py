from __future__ import annotations

from typing import Any, Protocol, TypedDict

from langgraph.graph import END, START, StateGraph

from app.modules.config_registry.schemas import AgentConfig, ModelConfig, SkillConfig
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


class AssistantHookAgentRuntimeState(TypedDict, total=False):
    context: AssistantHookExecutionContext
    agent_id: str
    input_mapping: dict[str, str]
    agent: AgentConfig
    skill: SkillConfig
    prompt: str
    system_prompt: str | None
    model: ModelConfig
    response_format: str
    raw_output: dict[str, Any]
    result: Any


class AssistantHookAgentRuntime(Protocol):
    async def run(
        self,
        context: AssistantHookExecutionContext,
        *,
        agent_id: str,
        input_mapping: dict[str, str],
    ) -> Any: ...


class LangGraphAssistantHookAgentRuntime:
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
        self._graph = self._build_graph()

    async def run(
        self,
        context: AssistantHookExecutionContext,
        *,
        agent_id: str,
        input_mapping: dict[str, str],
    ) -> Any:
        final_state = await self._graph.ainvoke(
            {
                "context": context,
                "agent_id": agent_id,
                "input_mapping": dict(input_mapping),
            }
        )
        if "result" not in final_state:
            raise ConfigurationError("Assistant hook agent runtime completed without result")
        return final_state["result"]

    def _build_graph(self):
        graph = StateGraph(AssistantHookAgentRuntimeState)
        graph.add_node("resolve_agent", self._resolve_agent)
        graph.add_node("prepare_request", self._prepare_request)
        graph.add_node("call_llm", self._call_llm)
        graph.add_node("resolve_output", self._resolve_output)
        graph.add_edge(START, "resolve_agent")
        graph.add_edge("resolve_agent", "prepare_request")
        graph.add_edge("prepare_request", "call_llm")
        graph.add_edge("call_llm", "resolve_output")
        graph.add_edge("resolve_output", END)
        return graph.compile(name="assistant_hook_agent_runtime")

    def _resolve_agent(
        self,
        state: AssistantHookAgentRuntimeState,
    ) -> AssistantHookAgentRuntimeState:
        context = state["context"]
        agent = self.assistant_agent_service.resolve_agent(
            state["agent_id"],
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
        return {
            "agent": agent,
            "skill": skill,
        }

    async def _prepare_request(
        self,
        state: AssistantHookAgentRuntimeState,
    ) -> AssistantHookAgentRuntimeState:
        context = state["context"]
        agent = state["agent"]
        skill = state["skill"]
        variables = build_hook_agent_variables(context, state["input_mapping"])
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
        return {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "model": model,
            "response_format": hook_agent_response_format(agent),
        }

    async def _call_llm(
        self,
        state: AssistantHookAgentRuntimeState,
    ) -> AssistantHookAgentRuntimeState:
        context = state["context"]
        raw_output = await self.llm_caller(
            context.db,
            prompt=state["prompt"],
            system_prompt=state["system_prompt"],
            model=state["model"],
            owner_id=context.owner_id,
            project_id=context.project_id,
            response_format=state["response_format"],
        )
        return {"raw_output": raw_output}

    def _resolve_output(
        self,
        state: AssistantHookAgentRuntimeState,
    ) -> AssistantHookAgentRuntimeState:
        agent = state["agent"]
        raw_output = state["raw_output"]
        return {"result": resolve_hook_agent_output(agent, raw_output.get("content"))}
