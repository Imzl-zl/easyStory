from __future__ import annotations

import asyncio
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry.schemas.config_schemas import ModelConfig, WorkflowConfig
from app.modules.credential.models import ModelCredential
from app.modules.credential.service.credential_connection_support import build_runtime_credential_payload
from app.modules.workflow.models import WorkflowExecution
from app.shared.runtime.errors import BudgetExceededError, ConfigurationError
from app.shared.runtime.llm_tool_provider import LLM_GENERATE_TOOL

from .workflow_runtime_llm_support import (
    ResolvedLLMCandidate,
    build_fallback_exhausted_error,
    capability_failures,
    fallback_model_names,
    retry_delay_seconds,
    should_retry_llm_error,
)


class WorkflowRuntimeLlmMixin:
    async def _call_llm(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        prompt_bundle: dict[str, Any],
        *,
        owner_id: uuid.UUID,
        node_execution_id: uuid.UUID | None,
        usage_type: str,
        credential: ModelCredential | None = None,
    ) -> dict[str, Any]:
        candidates = await self._build_llm_candidates(
            db,
            workflow,
            workflow_config,
            prompt_bundle["model"],
            owner_id=owner_id,
            credential=credential,
        )
        enabled_fallback = workflow_config.model_fallback.enabled
        attempted_models: list[str] = []
        skipped_models: list[str] = []
        last_error: Exception | None = None
        for candidate in candidates:
            failures = capability_failures(candidate, prompt_bundle)
            if failures:
                skipped_models.append(candidate.label)
                self._record_execution_log(
                    db,
                    workflow_execution_id=workflow.id,
                    node_execution_id=node_execution_id,
                    level="WARNING",
                    message="LLM candidate skipped by capability check",
                    details={"model_name": candidate.label, "capabilities": failures, "source": candidate.source},
                )
                continue
            attempted_models.append(candidate.label)
            try:
                raw_output = await self._execute_model_candidate(
                    db,
                    workflow,
                    workflow_config,
                    prompt_bundle,
                    candidate,
                    node_execution_id=node_execution_id,
                    usage_type=usage_type,
                    owner_id=owner_id,
                )
                return raw_output
            except BudgetExceededError:
                raise
            except Exception as exc:
                last_error = exc
                if not enabled_fallback:
                    raise
        raise build_fallback_exhausted_error(
            workflow_config,
            attempted_models=attempted_models,
            skipped_models=skipped_models,
            last_error=last_error,
        )

    async def _build_llm_candidates(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        base_model: ModelConfig,
        *,
        owner_id: uuid.UUID,
        credential: ModelCredential | None,
    ) -> list[ResolvedLLMCandidate]:
        candidates = [
            await self._resolve_llm_candidate(
                db,
                workflow,
                base_model,
                owner_id=owner_id,
                credential=credential,
                source="primary",
            )
        ]
        if not workflow_config.model_fallback.enabled:
            return candidates
        seen = {candidates[0].label}
        for fallback_name in fallback_model_names(base_model, workflow_config):
            if fallback_name in seen:
                continue
            seen.add(fallback_name)
            fallback_model = base_model.model_copy(update={"name": fallback_name})
            candidates.append(
                await self._resolve_llm_candidate(
                    db,
                    workflow,
                    fallback_model,
                    owner_id=owner_id,
                    credential=credential,
                    source="fallback",
                )
            )
        return candidates

    async def _resolve_llm_candidate(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        model: ModelConfig,
        *,
        owner_id: uuid.UUID,
        credential: ModelCredential | None,
        source: str,
    ) -> ResolvedLLMCandidate:
        if credential is not None:
            resolved_name = model.name or credential.default_model
            if not resolved_name:
                raise ConfigurationError("Fallback candidate is missing executable model name")
            return ResolvedLLMCandidate(
                model=model.model_copy(update={"name": resolved_name}),
                credential=credential,
                source=source,
            )
        resolved = await self._resolve_credential_service().resolve_active_credential_model(
            db,
            provider=model.provider or "",
            requested_model_name=model.name,
            user_id=owner_id,
            project_id=workflow.project_id,
        )
        return ResolvedLLMCandidate(
            model=model.model_copy(update={"name": resolved.model_name}),
            credential=resolved.credential,
            source=source,
        )

    async def _execute_model_candidate(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        prompt_bundle: dict[str, Any],
        candidate: ResolvedLLMCandidate,
        *,
        node_execution_id: uuid.UUID | None,
        usage_type: str,
        owner_id: uuid.UUID,
    ) -> dict[str, Any]:
        raw_output = await self._run_candidate_request(
            db,
            workflow,
            workflow_config,
            prompt_bundle,
            candidate,
            node_execution_id=node_execution_id,
        )
        return await self._record_candidate_usage(
            db,
            workflow,
            workflow_config,
            candidate,
            raw_output,
            node_execution_id=node_execution_id,
            usage_type=usage_type,
            owner_id=owner_id,
        )

    async def _run_candidate_request(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        prompt_bundle: dict[str, Any],
        candidate: ResolvedLLMCandidate,
        *,
        node_execution_id: uuid.UUID | None,
    ) -> dict[str, Any]:
        attempts = workflow_config.retry.max_attempts if workflow_config.retry.strategy != "none" else 1
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                return await self.tool_provider.execute(
                    LLM_GENERATE_TOOL,
                    {
                        "prompt": prompt_bundle["prompt"],
                        "system_prompt": prompt_bundle["system_prompt"],
                        "model": candidate.model.model_dump(mode="json", exclude_none=True),
                        "credential": build_runtime_credential_payload(
                            candidate.credential,
                            decrypt_api_key=self._resolve_credential_service().crypto.decrypt,
                        ),
                        "response_format": prompt_bundle["response_format"],
                    },
                )
            except Exception as exc:
                last_error = exc
                if not should_retry_llm_error(workflow_config, exc, attempt):
                    break
                self._record_execution_log(
                    db,
                    workflow_execution_id=workflow.id,
                    node_execution_id=node_execution_id,
                    level="WARNING",
                    message="LLM request retry scheduled",
                    details={"model_name": candidate.label, "attempt": attempt, "error": str(exc)},
                )
                await asyncio.sleep(retry_delay_seconds(workflow_config, attempt))
        assert last_error is not None
        self._record_execution_log(
            db,
            workflow_execution_id=workflow.id,
            node_execution_id=node_execution_id,
            level="ERROR",
            message="LLM candidate failed",
            details={"model_name": candidate.label, "source": candidate.source, "error": str(last_error)},
        )
        raise last_error

    async def _record_candidate_usage(
        self,
        db: AsyncSession,
        workflow: WorkflowExecution,
        workflow_config: WorkflowConfig,
        candidate: ResolvedLLMCandidate,
        raw_output: dict[str, Any],
        *,
        node_execution_id: uuid.UUID | None,
        usage_type: str,
        owner_id: uuid.UUID,
    ) -> dict[str, Any]:
        usage_model_name = raw_output.get("model_name") or candidate.model.name
        if not usage_model_name:
            raise ConfigurationError("LLM candidate usage is missing model_name")
        budget_result = await self.billing_service.record_usage_and_check_budget(
            db,
            workflow_execution_id=workflow.id,
            project_id=workflow.project_id,
            user_id=owner_id,
            node_execution_id=node_execution_id,
            credential_id=candidate.credential.id,
            usage_type=usage_type,
            model_name=usage_model_name,
            input_tokens=raw_output.get("input_tokens"),
            output_tokens=raw_output.get("output_tokens"),
            budget_config=workflow_config.budget,
        )
        self._record_budget_warnings(
            db,
            workflow_execution_id=workflow.id,
            node_execution_id=node_execution_id,
            budget_result=budget_result,
        )
        exceeded = budget_result.exceeded_status
        if exceeded is not None:
            raise BudgetExceededError(
                self._budget_exceeded_message(exceeded.scope, exceeded.used_tokens, exceeded.limit_tokens),
                action=workflow_config.budget.on_exceed,
                scope=exceeded.scope,
                used_tokens=exceeded.used_tokens,
                limit_tokens=exceeded.limit_tokens,
                usage_type=usage_type,
                raw_output=raw_output,
            )
        return raw_output
