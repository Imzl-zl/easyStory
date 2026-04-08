from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config_registry.schemas import ModelConfig
from app.modules.credential.service import (
    CredentialService,
    RuntimeCredentialPayload,
    build_runtime_credential_payload,
)
from app.shared.runtime import ToolProvider
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError
from app.shared.runtime.llm.interop.provider_tool_conformance_support import (
    ConformanceProbeKind,
    conformance_probe_kind_satisfies,
    normalize_conformance_probe_kind,
)
from app.shared.runtime.llm.llm_protocol import (
    LLMContinuationSupport,
    allows_provider_continuation_state,
    resolve_connection_continuation_support,
)
from app.shared.runtime.llm.llm_tool_provider import (
    LLM_GENERATE_TOOL,
    LLMGenerateToolResponse,
    LLMStreamEvent,
)

from .tooling.assistant_tool_loop import AssistantToolLoopModelStreamEvent


@dataclass(frozen=True)
class ResolvedAssistantLlmRuntime:
    credential_payload: RuntimeCredentialPayload
    continuation_support: LLMContinuationSupport
    credential_display_name: str
    verified_probe_kind: ConformanceProbeKind | None = None
    context_window_tokens: int | None = None
    default_max_output_tokens: int | None = None


async def resolve_assistant_llm_runtime(
    db: AsyncSession,
    *,
    credential_service: CredentialService,
    model: ModelConfig,
    owner_id: uuid.UUID,
    project_id: uuid.UUID | None,
) -> ResolvedAssistantLlmRuntime:
    credential = await credential_service.resolve_active_credential(
        db,
        provider=model.provider or "",
        user_id=owner_id,
        project_id=project_id,
    )
    credential_payload = build_runtime_credential_payload(
        credential,
        decrypt_api_key=credential_service.crypto.decrypt,
    )
    return ResolvedAssistantLlmRuntime(
        credential_payload=credential_payload,
        continuation_support=resolve_connection_continuation_support(
            credential.api_dialect,
            credential.interop_profile,
        ),
        credential_display_name=credential.display_name,
        verified_probe_kind=(
            normalize_conformance_probe_kind(credential.verified_probe_kind)
            if credential.verified_probe_kind is not None
            else None
        ),
        context_window_tokens=credential.context_window_tokens,
        default_max_output_tokens=credential.default_max_output_tokens,
    )


async def call_assistant_llm(
    *,
    tool_provider: ToolProvider,
    prompt: str,
    system_prompt: str | None,
    model: ModelConfig,
    resolved_runtime: ResolvedAssistantLlmRuntime,
    response_format: str = "text",
    tools: list[dict[str, Any]] | None = None,
    continuation_items: list[dict[str, Any]] | None = None,
    provider_continuation_state: dict[str, Any] | None = None,
) -> LLMGenerateToolResponse:
    return await tool_provider.execute(
        LLM_GENERATE_TOOL,
        {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "model": serialize_assistant_model_config(model),
            "credential": resolved_runtime.credential_payload,
            "response_format": response_format,
            "tools": list(tools or []),
            "continuation_items": list(continuation_items or []),
            "provider_continuation_state": sanitize_provider_continuation_state(
                provider_continuation_state,
                continuation_support=resolved_runtime.continuation_support,
            ),
        },
    )


async def stream_assistant_llm(
    *,
    tool_provider: ToolProvider,
    prompt: str,
    system_prompt: str | None,
    model: ModelConfig,
    resolved_runtime: ResolvedAssistantLlmRuntime,
    tools: list[dict[str, Any]] | None = None,
    continuation_items: list[dict[str, Any]] | None = None,
    provider_continuation_state: dict[str, Any] | None = None,
    should_stop: Callable[[], Awaitable[bool]] | None = None,
) -> AsyncIterator[LLMStreamEvent]:
    stream_executor = getattr(tool_provider, "execute_stream", None)
    if not callable(stream_executor):
        raise ConfigurationError("Current assistant runtime does not support streaming")
    async for event in stream_executor(
        LLM_GENERATE_TOOL,
        {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "model": serialize_assistant_model_config(model),
            "credential": resolved_runtime.credential_payload,
            "response_format": "text",
            "tools": list(tools or []),
            "continuation_items": list(continuation_items or []),
            "provider_continuation_state": sanitize_provider_continuation_state(
                provider_continuation_state,
                continuation_support=resolved_runtime.continuation_support,
            ),
        },
        should_stop=should_stop,
    ):
        yield event


def build_tool_loop_model_caller(
    *,
    llm_caller: Callable[..., Awaitable[LLMGenerateToolResponse]],
    db: AsyncSession,
    model: ModelConfig,
    owner_id: uuid.UUID,
    project_id: uuid.UUID | None,
    runtime_context: ResolvedAssistantLlmRuntime,
) -> Callable[..., Awaitable[LLMGenerateToolResponse]]:
    async def model_caller(
        *,
        prompt: str,
        system_prompt: str | None,
        tools: list[dict[str, Any]],
        continuation_items: list[dict[str, Any]] | None = None,
        provider_continuation_state: dict[str, Any] | None = None,
    ) -> LLMGenerateToolResponse:
        return await llm_caller(
            db,
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            owner_id=owner_id,
            project_id=project_id,
            runtime_context=runtime_context,
            tools=tools,
            continuation_items=continuation_items,
            provider_continuation_state=provider_continuation_state,
        )

    return model_caller


def build_tool_loop_stream_model_caller(
    *,
    llm_stream_caller: Callable[..., AsyncIterator[LLMStreamEvent]],
    db: AsyncSession,
    model: ModelConfig,
    owner_id: uuid.UUID,
    project_id: uuid.UUID | None,
    runtime_context: ResolvedAssistantLlmRuntime,
    should_stop: Callable[[], Awaitable[bool]] | None,
) -> Callable[..., AsyncIterator[AssistantToolLoopModelStreamEvent]]:
    async def stream_model_caller(
        *,
        prompt: str,
        system_prompt: str | None,
        tools: list[dict[str, Any]],
        continuation_items: list[dict[str, Any]] | None = None,
        provider_continuation_state: dict[str, Any] | None = None,
    ) -> AsyncIterator[AssistantToolLoopModelStreamEvent]:
        async for event in llm_stream_caller(
            db,
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            owner_id=owner_id,
            project_id=project_id,
            runtime_context=runtime_context,
            tools=tools,
            continuation_items=continuation_items,
            provider_continuation_state=provider_continuation_state,
            should_stop=should_stop,
        ):
            if event.delta:
                yield AssistantToolLoopModelStreamEvent(delta=event.delta)
                continue
            yield AssistantToolLoopModelStreamEvent(raw_output=event.response)

    return stream_model_caller


def sanitize_provider_continuation_state(
    provider_continuation_state: dict[str, Any] | None,
    *,
    continuation_support: LLMContinuationSupport,
) -> dict[str, Any] | None:
    if not allows_provider_continuation_state(continuation_support):
        return None
    return provider_continuation_state


def serialize_assistant_model_config(model: ModelConfig) -> dict[str, Any]:
    payload = model.model_dump(mode="json", exclude_none=True)
    if "max_tokens" not in model.model_fields_set:
        payload.pop("max_tokens", None)
    return payload


def resolve_assistant_max_output_tokens(
    model: ModelConfig,
    *,
    resolved_runtime: ResolvedAssistantLlmRuntime,
) -> int | None:
    if "max_tokens" in model.model_fields_set:
        return model.max_tokens
    return resolved_runtime.default_max_output_tokens


def ensure_assistant_runtime_supports_visible_tools(
    resolved_runtime: ResolvedAssistantLlmRuntime,
    *,
    visible_tool_names: tuple[str, ...],
) -> None:
    if not visible_tool_names:
        return
    if conformance_probe_kind_satisfies(
        resolved_runtime.verified_probe_kind,
        required_probe_kind="tool_continuation_probe",
    ):
        return
    raise BusinessRuleError(
        f"模型连接“{resolved_runtime.credential_display_name}”尚未通过“验证工具”，"
        "当前不能启用项目工具。请先到模型连接中执行“验证工具”。"
    )
