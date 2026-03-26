from __future__ import annotations

from dataclasses import dataclass
import httpx
from typing import Any

from app.modules.config_registry.schemas.config_schemas import ModelConfig, WorkflowConfig
from app.modules.credential.models import ModelCredential
from app.shared.runtime.errors import ConfigurationError, ModelFallbackExhaustedError

MODEL_FALLBACK_PAUSE_REASON = "model_fallback_exhausted"
JSON_OBJECT_CAPABILITY = "json_schema_output"
JSON_OBJECT_RESPONSE_FORMAT = "json_object"
JSON_OBJECT_COMPATIBLE_DIALECTS = frozenset(
    {"openai_chat_completions", "openai_responses", "gemini_generate_content"}
)
KNOWN_CAPABILITIES = frozenset(
    {"json_schema_output", "long_context", "streaming", "tool_calling"}
)


@dataclass(frozen=True)
class ResolvedLLMCandidate:
    model: ModelConfig
    credential: ModelCredential
    source: str

    @property
    def label(self) -> str:
        return self.model.name or "<default>"


def fallback_model_names(
    base_model: ModelConfig,
    workflow_config: WorkflowConfig,
) -> list[str]:
    names: list[str] = []
    for item in workflow_config.model_fallback.chain:
        model_name = item.model.strip()
        if not model_name:
            raise ConfigurationError("model_fallback.chain entries must be non-empty model names")
        names.append(model_name)
    if base_model.name:
        names.insert(0, base_model.name)
    return names


def capability_failures(
    candidate: ResolvedLLMCandidate,
    prompt_bundle: dict[str, Any],
) -> list[str]:
    response_format = prompt_bundle.get("response_format")
    failures: list[str] = []
    for capability in candidate.model.required_capabilities:
        normalized = capability.strip()
        if not normalized:
            continue
        if normalized not in KNOWN_CAPABILITIES:
            failures.append(normalized)
            continue
        if normalized != JSON_OBJECT_CAPABILITY or response_format != JSON_OBJECT_RESPONSE_FORMAT:
            continue
        if candidate.credential.api_dialect not in JSON_OBJECT_COMPATIBLE_DIALECTS:
            failures.append(normalized)
    return failures


def should_retry_llm_error(
    workflow_config: WorkflowConfig,
    exc: Exception,
    attempt: int,
) -> bool:
    if attempt >= workflow_config.retry.max_attempts or workflow_config.retry.strategy == "none":
        return False
    category = _retryable_error_category(exc)
    return category is not None and category in workflow_config.retry.retryable_errors


def retry_delay_seconds(workflow_config: WorkflowConfig, attempt: int) -> float:
    if workflow_config.retry.strategy == "fixed":
        return workflow_config.retry.initial_delay
    return min(
        workflow_config.retry.initial_delay * (2 ** max(attempt - 1, 0)),
        workflow_config.retry.max_delay,
    )


def build_fallback_exhausted_error(
    workflow_config: WorkflowConfig,
    *,
    attempted_models: list[str],
    skipped_models: list[str],
    last_error: Exception | None,
) -> ModelFallbackExhaustedError:
    detail = str(last_error) if last_error is not None else "没有可执行的兼容候选模型"
    return ModelFallbackExhaustedError(
        f"模型回退链已耗尽：{detail}",
        action=workflow_config.model_fallback.on_all_fail,
        attempted_models=attempted_models,
        skipped_models=skipped_models,
        last_error=detail,
    )


def _retryable_error_category(exc: Exception) -> str | None:
    message = str(exc).lower()
    if isinstance(exc, httpx.TimeoutException) or "timeout" in message:
        return "timeout"
    if isinstance(exc, httpx.RequestError):
        return "server_error"
    if "http 429" in message:
        return "rate_limit"
    if "http 5" in message:
        return "server_error"
    return None
