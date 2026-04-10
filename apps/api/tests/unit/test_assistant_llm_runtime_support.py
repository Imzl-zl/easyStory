from app.modules.assistant.service.assistant_llm_runtime_support import (
    ResolvedAssistantLlmRuntime,
    resolve_assistant_output_budget_tokens,
)
from app.modules.config_registry.schemas import ModelConfig
from app.shared.runtime.llm.llm_protocol import LLMContinuationSupport


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
