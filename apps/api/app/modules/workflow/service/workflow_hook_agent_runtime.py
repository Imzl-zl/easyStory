from __future__ import annotations

from typing import Any, Callable, Protocol, TypedDict

from langgraph.graph import END, START, StateGraph

from app.shared.runtime.template_renderer import SkillTemplateRenderer
from app.shared.runtime.errors import ConfigurationError

from .snapshot_support import load_agent_snapshot, load_skill_snapshot
from .workflow_runtime_hook_support import HookExecutionContext


class WorkflowHookAgentLlmCaller(Protocol):
    async def __call__(
        self,
        db,
        workflow,
        workflow_config,
        prompt_bundle: dict[str, Any],
        *,
        owner_id,
        node_execution_id,
        usage_type: str,
        credential=None,
    ) -> dict[str, Any]: ...


class WorkflowHookAgentRuntimeState(TypedDict, total=False):
    context: HookExecutionContext
    agent_id: str
    input_mapping: dict[str, str]
    agent: Any
    skill: Any
    prompt_bundle: dict[str, Any]
    raw_output: dict[str, Any]
    result: Any


class LangGraphWorkflowHookAgentRuntime:
    def __init__(
        self,
        *,
        template_renderer: SkillTemplateRenderer,
        llm_caller: WorkflowHookAgentLlmCaller,
        parse_json: Callable[[Any], Any],
    ) -> None:
        self.template_renderer = template_renderer
        self.llm_caller = llm_caller
        self.parse_json = parse_json
        self._graph = self._build_graph()

    async def run(
        self,
        context: HookExecutionContext,
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
            raise ConfigurationError("Workflow hook agent runtime completed without result")
        return final_state["result"]

    def _build_graph(self):
        graph = StateGraph(WorkflowHookAgentRuntimeState)
        graph.add_node("resolve_agent", self._resolve_agent)
        graph.add_node("prepare_request", self._prepare_request)
        graph.add_node("call_llm", self._call_llm)
        graph.add_node("resolve_output", self._resolve_output)
        graph.add_edge(START, "resolve_agent")
        graph.add_edge("resolve_agent", "prepare_request")
        graph.add_edge("prepare_request", "call_llm")
        graph.add_edge("call_llm", "resolve_output")
        graph.add_edge("resolve_output", END)
        return graph.compile(name="workflow_hook_agent_runtime")

    def _resolve_agent(
        self,
        state: WorkflowHookAgentRuntimeState,
    ) -> WorkflowHookAgentRuntimeState:
        context = state["context"]
        agent = load_agent_snapshot(context.workflow.agents_snapshot or {}, state["agent_id"])
        if not agent.skills:
            raise ConfigurationError(f"Hook agent {agent.id} has no skills configured")
        skill = load_skill_snapshot(context.workflow.skills_snapshot or {}, agent.skills[0])
        return {
            "agent": agent,
            "skill": skill,
        }

    def _prepare_request(
        self,
        state: WorkflowHookAgentRuntimeState,
    ) -> WorkflowHookAgentRuntimeState:
        context = state["context"]
        agent = state["agent"]
        skill = state["skill"]
        variables = _build_hook_agent_variables(context, state["input_mapping"])
        prompt = self.template_renderer.render(skill.prompt, variables)
        model = agent.model or skill.model
        if model is None or not model.provider:
            raise ConfigurationError(f"Hook agent {agent.id} is missing model configuration")
        return {
            "prompt_bundle": {
                "prompt": prompt,
                "system_prompt": agent.system_prompt,
                "model": model,
                "response_format": _resolve_hook_agent_response_format(agent),
            }
        }

    async def _call_llm(
        self,
        state: WorkflowHookAgentRuntimeState,
    ) -> WorkflowHookAgentRuntimeState:
        context = state["context"]
        raw_output = await self.llm_caller(
            context.db,
            context.workflow,
            context.workflow_config,
            state["prompt_bundle"],
            owner_id=context.owner_id,
            node_execution_id=context.node_execution_id,
            usage_type="analysis",
        )
        return {"raw_output": raw_output}

    def _resolve_output(
        self,
        state: WorkflowHookAgentRuntimeState,
    ) -> WorkflowHookAgentRuntimeState:
        agent = state["agent"]
        content = state["raw_output"].get("content")
        if _resolve_hook_agent_response_format(agent) == "json_object":
            return {"result": self.parse_json(content)}
        if not isinstance(content, str):
            raise ConfigurationError("Hook agent output must be plain text")
        return {"result": content}


def _build_hook_agent_variables(
    context: HookExecutionContext,
    input_mapping: dict[str, str],
) -> dict[str, Any]:
    variables: dict[str, Any] = {
        "payload": context.payload,
        "payload_json": context.payload_json(),
        "event": context.event,
        "node_id": context.node.id,
        "node_name": context.node.name,
        "node_type": context.node.node_type,
        "workflow_id": context.workflow_config.id,
    }
    for target, source in input_mapping.items():
        variables[target] = context.read_path(source)
    return variables


def _resolve_hook_agent_response_format(agent) -> str:
    if agent.output_schema is not None or agent.agent_type == "reviewer":
        return "json_object"
    return "text"
