import pytest

from app.modules.assistant.service.assistant_llm_runtime_support import (
    ResolvedAssistantLlmRuntime,
    ensure_assistant_tool_capability,
    resolve_assistant_output_budget_tokens,
)
from app.modules.config_registry.schemas import ModelConfig
from app.shared.runtime.errors import BusinessRuleError
from app.shared.runtime.llm.llm_protocol_types import LLMContinuationSupport


def test_resolve_assistant_output_budget_tokens_clamps_anthropic_default_to_context_window() -> None:
    resolved = resolve_assistant_output_budget_tokens(
        ModelConfig(provider="anthropic", name="claude-sonnet-4"),
        resolved_runtime=ResolvedAssistantLlmRuntime(
            credential_payload={
                "provider": "anthropic",
                "api_key": "test-key",
                "api_dialect": "anthropic_messages",
                "base_url": "https://api.anthropic.com",
                "default_model": "claude-sonnet-4",
                "interop_profile": None,
                "context_window_tokens": 4096,
                "default_max_output_tokens": None,
                "auth_strategy": "x_api_key",
                "api_key_header_name": None,
                "extra_headers": None,
                "user_agent_override": None,
                "client_name": None,
                "client_version": None,
                "runtime_kind": None,
            },
            continuation_support=LLMContinuationSupport(
                continuation_mode="runtime_replay",
                tolerates_interleaved_tool_results=False,
                requires_full_replay_after_local_tools=True,
            ),
            credential_display_name="Anthropic",
            context_window_tokens=4096,
            default_max_output_tokens=None,
        ),
    )

    assert resolved == 4095


def test_ensure_assistant_tool_capability_rejects_missing_buffered_tool_probe() -> None:
    resolved_runtime = ResolvedAssistantLlmRuntime(
        credential_payload={
            "provider": "openai",
            "api_key": "test-key",
            "api_dialect": "openai_responses",
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4o-mini",
            "interop_profile": "responses_strict",
            "context_window_tokens": None,
            "default_max_output_tokens": None,
            "auth_strategy": "bearer",
            "api_key_header_name": None,
            "extra_headers": None,
            "user_agent_override": None,
            "client_name": None,
            "client_version": None,
            "runtime_kind": None,
        },
        continuation_support=LLMContinuationSupport(
            continuation_mode="provider_native",
            tolerates_interleaved_tool_results=False,
            requires_full_replay_after_local_tools=False,
        ),
        credential_display_name="OpenAI 测试连接",
        stream_tool_verified_probe_kind="tool_continuation_probe",
        buffered_tool_verified_probe_kind=None,
    )

    with pytest.raises(BusinessRuleError, match="未完成非流工具调用验证"):
        ensure_assistant_tool_capability(
            resolved_runtime,
            visible_tool_names=("project.read_documents",),
            transport_mode="buffered",
        )


def test_ensure_assistant_tool_capability_allows_stream_tools_after_verified_probe() -> None:
    resolved_runtime = ResolvedAssistantLlmRuntime(
        credential_payload={
            "provider": "openai",
            "api_key": "test-key",
            "api_dialect": "openai_responses",
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4o-mini",
            "interop_profile": "responses_strict",
            "context_window_tokens": None,
            "default_max_output_tokens": None,
            "auth_strategy": "bearer",
            "api_key_header_name": None,
            "extra_headers": None,
            "user_agent_override": None,
            "client_name": None,
            "client_version": None,
            "runtime_kind": None,
        },
        continuation_support=LLMContinuationSupport(
            continuation_mode="provider_native",
            tolerates_interleaved_tool_results=False,
            requires_full_replay_after_local_tools=False,
        ),
        credential_display_name="OpenAI 测试连接",
        stream_tool_verified_probe_kind="tool_continuation_probe",
        buffered_tool_verified_probe_kind="tool_call_probe",
    )

    ensure_assistant_tool_capability(
        resolved_runtime,
        visible_tool_names=("project.read_documents",),
        transport_mode="stream",
    )
