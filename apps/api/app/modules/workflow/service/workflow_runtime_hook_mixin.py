from __future__ import annotations

import asyncio
from typing import Any

from app.shared.runtime.errors import ConfigurationError

from .workflow_hook_event_runtime import WorkflowHookEventRuntime
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
        runtime = WorkflowHookEventRuntime(
            resolve_hooks=lambda: resolve_hooks_for_event(
                context.workflow.workflow_snapshot or {},
                context.node,
                context.event,
            ),
            matches_condition=lambda hook: matches_hook_condition(hook, context.payload),
            record_skip=lambda hook: self._record_hook_skip(context, hook.id),
            execute_hook=lambda hook: self._execute_hook_with_retry(context, hook),
            record_success=lambda hook, result: self._record_hook_success(context, hook, result),
        )
        return await runtime.run()

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
        return await self.workflow_hook_agent_runtime.run(
            context,
            agent_id=agent_id,
            input_mapping=input_mapping,
        )

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
