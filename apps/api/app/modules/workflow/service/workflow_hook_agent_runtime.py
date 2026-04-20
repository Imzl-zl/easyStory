from __future__ import annotations

from typing import Any, Callable, Protocol

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

    async def run(
        self,
        context: HookExecutionContext,
        *,
        agent_id: str,
        input_mapping: dict[str, str],
    ) -> Any:
        agent = load_agent_snapshot(context.workflow.agents_snapshot or {}, agent_id)
        if not agent.skills:
            raise ConfigurationError(f"Hook agent {agent.id} has no skills configured")
        skill = load_skill_snapshot(context.workflow.skills_snapshot or {}, agent.skills[0])
        variables = _build_hook_agent_variables(context, input_mapping)
        prompt = self.template_renderer.render(skill.prompt, variables)
        model = agent.model or skill.model
        if model is None or not model.provider:
            raise ConfigurationError(f"Hook agent {agent.id} is missing model configuration")
        prompt_bundle = {
            "prompt": prompt,
            "system_prompt": agent.system_prompt,
            "model": model,
            "response_format": _resolve_hook_agent_response_format(agent),
        }
        raw_output = await self.llm_caller(
            context.db,
            context.workflow,
            context.workflow_config,
            prompt_bundle,
            owner_id=context.owner_id,
            node_execution_id=context.node_execution_id,
            usage_type="analysis",
        )
        content = raw_output.get("content")
        if _resolve_hook_agent_response_format(agent) == "json_object":
            return self.parse_json(content)
        if not isinstance(content, str):
            raise ConfigurationError("Hook agent output must be plain text")
        return content


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
