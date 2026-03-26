from __future__ import annotations

import asyncio
from typing import Any

from app.shared.runtime.errors import ConfigurationError

from .snapshot_support import load_agent_snapshot, load_skill_snapshot
from .workflow_runtime_hook_support import (
    HookExecutionContext,
    build_hook_payload,
    matches_hook_condition,
    normalize_hook_result,
    resolve_hooks_for_event,
    serialize_hook_error,
)


class WorkflowRuntimeHookMixin:
    async def _run_hook_event(
        self,
        context: HookExecutionContext,
    ) -> list[Any]:
        hooks = resolve_hooks_for_event(
            context.workflow.workflow_snapshot or {},
            context.node,
            context.event,
        )
        results: list[Any] = []
        for hook in hooks:
            if not matches_hook_condition(hook, context.payload):
                self._record_hook_skip(context, hook.id)
                continue
            result = await self._execute_hook_with_retry(context, hook)
            self._record_hook_success(context, hook, result)
            results.append(result)
        return results

    async def _execute_hook_with_retry(
        self,
        context: HookExecutionContext,
        hook,
    ) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, self._hook_attempts(hook) + 1):
            try:
                return await self.plugin_registry.execute(
                    hook.action.action_type,
                    config=hook.action.config,
                    context=context,
                    timeout_seconds=hook.timeout,
                )
            except Exception as exc:
                last_error = exc
                if attempt >= self._hook_attempts(hook):
                    raise
                self._record_hook_retry(context, hook, attempt, exc)
                await asyncio.sleep(self._hook_delay(hook))
        assert last_error is not None
        raise last_error

    async def _run_on_error_hooks(
        self,
        context: HookExecutionContext,
        error: Exception,
    ) -> None:
        error_payload = dict(context.payload)
        error_payload["error"] = serialize_hook_error(error)
        error_context = HookExecutionContext(
            db=context.db,
            workflow=context.workflow,
            workflow_config=context.workflow_config,
            node=context.node,
            event="on_error",
            owner_id=context.owner_id,
            payload=error_payload,
            node_execution_id=context.node_execution_id,
        )
        try:
            await self._run_hook_event(error_context)
        except Exception as hook_exc:
            raise ExceptionGroup(
                "Workflow runtime error and on_error hook both failed",
                [error, hook_exc],
            ) from hook_exc

    async def run_agent_hook(
        self,
        context: HookExecutionContext,
        *,
        agent_id: str,
        input_mapping: dict[str, str],
    ) -> Any:
        agent = load_agent_snapshot(context.workflow.agents_snapshot or {}, agent_id)
        skill = self._resolve_hook_agent_skill(context, agent)
        prompt_bundle = self._build_hook_agent_prompt_bundle(context, agent, skill, input_mapping)
        raw_output = await self._call_llm(
            context.db,
            context.workflow,
            context.workflow_config,
            prompt_bundle,
            owner_id=context.owner_id,
            node_execution_id=context.node_execution_id,
            usage_type="analysis",
        )
        return self._resolve_hook_agent_output(agent, raw_output.get("content"))

    def _resolve_hook_agent_skill(self, context: HookExecutionContext, agent):
        if not agent.skills:
            raise ConfigurationError(f"Hook agent {agent.id} has no skills configured")
        return load_skill_snapshot(context.workflow.skills_snapshot or {}, agent.skills[0])

    def _build_hook_agent_prompt_bundle(
        self,
        context: HookExecutionContext,
        agent,
        skill,
        input_mapping: dict[str, str],
    ) -> dict[str, Any]:
        variables = self._hook_agent_variables(context, input_mapping)
        prompt = self.template_renderer.render(skill.prompt, variables)
        model = agent.model or skill.model
        if model is None or not model.provider:
            raise ConfigurationError(f"Hook agent {agent.id} is missing model configuration")
        return {
            "prompt": prompt,
            "system_prompt": agent.system_prompt,
            "model": model,
            "response_format": self._hook_agent_response_format(agent),
        }

    def _hook_agent_variables(
        self,
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

    def _hook_agent_response_format(self, agent) -> str:
        if agent.output_schema is not None or agent.agent_type == "reviewer":
            return "json_object"
        return "text"

    def _resolve_hook_agent_output(self, agent, content: Any) -> Any:
        if self._hook_agent_response_format(agent) == "json_object":
            return self._parse_json(content)
        if not isinstance(content, str):
            raise ConfigurationError("Hook agent output must be plain text")
        return content

    def _build_hook_context(
        self,
        db,
        workflow,
        workflow_config,
        node,
        event: str,
        *,
        owner_id,
        payload: dict[str, Any],
        node_execution_id=None,
    ) -> HookExecutionContext:
        return HookExecutionContext(
            db=db,
            workflow=workflow,
            workflow_config=workflow_config,
            node=node,
            event=event,
            owner_id=owner_id,
            payload=payload,
            node_execution_id=node_execution_id,
        )

    def _base_hook_payload(
        self,
        workflow,
        workflow_config,
        node,
        event: str,
        *,
        node_execution_id=None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return build_hook_payload(
            workflow,
            workflow_config,
            node,
            event,
            node_execution_id=node_execution_id,
            extra=extra,
        )

    def _record_hook_success(self, context: HookExecutionContext, hook, result: Any) -> None:
        self._record_execution_log(
            context.db,
            workflow_execution_id=context.workflow.id,
            node_execution_id=context.node_execution_id,
            level="INFO",
            message="Hook executed",
            details={
                "hook_id": hook.id,
                "event": context.event,
                "action_type": hook.action.action_type,
                "result": normalize_hook_result(result),
            },
        )

    def _record_hook_skip(self, context: HookExecutionContext, hook_id: str) -> None:
        self._record_execution_log(
            context.db,
            workflow_execution_id=context.workflow.id,
            node_execution_id=context.node_execution_id,
            level="INFO",
            message="Hook skipped",
            details={"hook_id": hook_id, "event": context.event, "reason": "condition_not_matched"},
        )

    def _record_hook_retry(self, context: HookExecutionContext, hook, attempt: int, exc: Exception) -> None:
        self._record_execution_log(
            context.db,
            workflow_execution_id=context.workflow.id,
            node_execution_id=context.node_execution_id,
            level="WARNING",
            message="Hook retry scheduled",
            details={
                "hook_id": hook.id,
                "event": context.event,
                "attempt": attempt,
                "error": serialize_hook_error(exc),
            },
        )

    def _hook_attempts(self, hook) -> int:
        max_attempts = hook.retry.max_attempts if hook.retry is not None else 1
        if max_attempts < 1:
            raise ConfigurationError("Hook retry.max_attempts must be >= 1")
        return max_attempts

    def _hook_delay(self, hook) -> int:
        delay = hook.retry.delay if hook.retry is not None else 0
        if delay < 0:
            raise ConfigurationError("Hook retry.delay must be >= 0")
        return delay
