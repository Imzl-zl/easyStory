from __future__ import annotations

import json

import pytest

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.interop.provider_interop_support import (
    ProviderInteropOverride,
    enforce_provider_interop_rate_limit,
    load_provider_interop_profiles,
    resolve_provider_interop_profile,
)
from app.shared.runtime.llm.interop.provider_tool_conformance_support import build_text_probe_request


def test_load_provider_interop_profiles_reads_local_json(tmp_path) -> None:
    config_path = tmp_path / "provider-interop.local.json"
    config_path.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "id": "gpt",
                        "provider": "openai",
                        "api_dialect": "openai_chat_completions",
                        "base_url": "https://proxy.example.com/v1",
                        "default_model": "gpt-5.2-codex",
                        "api_key_env": "TEST_GPT_API_KEY",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    profiles = load_provider_interop_profiles(config_path)

    assert len(profiles) == 1
    assert profiles[0].id == "gpt"
    assert profiles[0].default_model == "gpt-5.2-codex"


def test_load_provider_interop_profiles_reads_explicit_interop_profile(tmp_path) -> None:
    config_path = tmp_path / "provider-interop.local.json"
    config_path.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "id": "gpt",
                        "provider": "openai",
                        "api_dialect": "openai_responses",
                        "interop_profile": "responses_strict",
                        "base_url": "https://proxy.example.com/v1",
                        "default_model": "gpt-5.2-codex",
                        "api_key_env": "TEST_GPT_API_KEY",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    profiles = load_provider_interop_profiles(config_path)

    assert profiles[0].interop_profile == "responses_strict"


def test_resolve_provider_interop_profile_applies_override_and_env(tmp_path) -> None:
    config_path = tmp_path / "provider-interop.local.json"
    env_path = tmp_path / ".env.provider-interop.local"
    config_path.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "id": "anthropic",
                        "provider": "anthropic",
                        "api_dialect": "anthropic_messages",
                        "base_url": "https://api.anthropic.com",
                        "default_model": "claude-haiku",
                        "api_key_env": "TEST_ANTHROPIC_API_KEY",
                        "auth_strategy": "x_api_key",
                        "api_key_header_name": "x-api-key",
                        "extra_headers": {"HTTP-Referer": "https://app.example.com"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    env_path.write_text("TEST_ANTHROPIC_API_KEY=test-key\n", encoding="utf-8")

    resolved = resolve_provider_interop_profile(
        "anthropic",
        config_path=config_path,
        env_path=env_path,
        override=ProviderInteropOverride(
            auth_strategy="bearer",
            model_name="claude-haiku-override",
            base_url="https://proxy.example.com/v1/messages",
            extra_headers={"X-Trace-Id": "probe-001"},
        ),
    )

    assert resolved.model_name == "claude-haiku-override"
    assert resolved.connection.api_key == "test-key"
    assert resolved.connection.auth_strategy == "bearer"
    assert resolved.connection.api_key_header_name is None
    assert resolved.connection.base_url == "https://proxy.example.com/v1/messages"
    assert resolved.connection.default_model == "claude-haiku-override"
    assert resolved.connection.extra_headers == {
        "HTTP-Referer": "https://app.example.com",
        "X-Trace-Id": "probe-001",
    }

    request = build_text_probe_request(resolved.connection, model_name=resolved.model_name)

    assert request.model_name == "claude-haiku-override"
    assert request.connection.base_url == "https://proxy.example.com/v1/messages"


def test_build_text_probe_request_supports_custom_prompt(tmp_path) -> None:
    config_path = tmp_path / "provider-interop.local.json"
    env_path = tmp_path / ".env.provider-interop.local"
    config_path.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "id": "gpt",
                        "provider": "openai",
                        "api_dialect": "openai_responses",
                        "base_url": "https://proxy.example.com/v1",
                        "default_model": "gpt-5.2-codex",
                        "api_key_env": "TEST_GPT_API_KEY",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    env_path.write_text("TEST_GPT_API_KEY=test-key\n", encoding="utf-8")

    resolved = resolve_provider_interop_profile(
        "gpt",
        config_path=config_path,
        env_path=env_path,
    )

    request = build_text_probe_request(
        resolved.connection,
        model_name=resolved.model_name,
        prompt="今天有什么新闻",
        system_prompt="请直接回答用户问题。",
    )

    assert request.model_name == "gpt-5.2-codex"
    assert request.prompt == "今天有什么新闻"
    assert request.system_prompt == "请直接回答用户问题。"
    assert request.response_format == "text"


def test_resolve_provider_interop_profile_preserves_interop_profile_into_request(tmp_path) -> None:
    config_path = tmp_path / "provider-interop.local.json"
    env_path = tmp_path / ".env.provider-interop.local"
    config_path.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "id": "gpt",
                        "provider": "openai",
                        "api_dialect": "openai_responses",
                        "interop_profile": "responses_strict",
                        "base_url": "https://proxy.example.com/v1",
                        "default_model": "gpt-5.2-codex",
                        "api_key_env": "TEST_GPT_API_KEY",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    env_path.write_text("TEST_GPT_API_KEY=test-key\n", encoding="utf-8")

    resolved = resolve_provider_interop_profile(
        "gpt",
        config_path=config_path,
        env_path=env_path,
    )

    request = build_text_probe_request(
        resolved.connection,
        model_name=resolved.model_name,
        prompt="今天有什么新闻",
    )

    assert resolved.connection.interop_profile == "responses_strict"
    assert request.connection.interop_profile == "responses_strict"


def test_build_text_probe_request_keeps_gemini_shape_aligned_with_runtime(tmp_path) -> None:
    config_path = tmp_path / "provider-interop.local.json"
    env_path = tmp_path / ".env.provider-interop.local"
    config_path.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "id": "gemini",
                        "provider": "gemini",
                        "api_dialect": "gemini_generate_content",
                        "base_url": "https://example.com",
                        "default_model": "gemini-flash-latest",
                        "api_key_env": "TEST_GEMINI_API_KEY",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    env_path.write_text("TEST_GEMINI_API_KEY=test-key\n", encoding="utf-8")

    resolved = resolve_provider_interop_profile(
        "gemini",
        config_path=config_path,
        env_path=env_path,
    )

    default_request = build_text_probe_request(resolved.connection, model_name=resolved.model_name)
    custom_request = build_text_probe_request(
        resolved.connection,
        model_name=resolved.model_name,
        prompt="今天有什么新闻",
        system_prompt="请直接回答用户问题。",
    )

    assert default_request.connection.api_dialect == "gemini_generate_content"
    assert default_request.max_tokens == 256
    assert default_request.temperature == 0.0
    assert default_request.top_p == 1.0
    assert default_request.thinking_budget is None
    assert custom_request.thinking_budget is None


def test_resolve_provider_interop_profile_requires_custom_header_name(tmp_path) -> None:
    config_path = tmp_path / "provider-interop.local.json"
    env_path = tmp_path / ".env.provider-interop.local"
    config_path.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "id": "gemini",
                        "provider": "gemini",
                        "api_dialect": "gemini_generate_content",
                        "base_url": "https://example.com",
                        "default_model": "gemini-flash-latest",
                        "api_key_env": "TEST_GEMINI_API_KEY",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    env_path.write_text("TEST_GEMINI_API_KEY=test-key\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="requires api_key_header_name"):
        resolve_provider_interop_profile(
            "gemini",
            config_path=config_path,
            env_path=env_path,
            override=ProviderInteropOverride(auth_strategy="custom_header"),
        )


def test_enforce_provider_interop_rate_limit_blocks_excess_requests(tmp_path) -> None:
    rate_limit_path = tmp_path / "provider-interop.rate-limit.json"

    enforce_provider_interop_rate_limit(
        profile_id="gemini",
        max_requests_per_minute=2,
        rate_limit_path=rate_limit_path,
        now_seconds=120,
    )
    enforce_provider_interop_rate_limit(
        profile_id="gemini",
        max_requests_per_minute=2,
        rate_limit_path=rate_limit_path,
        now_seconds=121,
    )

    with pytest.raises(ConfigurationError, match="Local rate limit exceeded"):
        enforce_provider_interop_rate_limit(
            profile_id="gemini",
            max_requests_per_minute=2,
            rate_limit_path=rate_limit_path,
            now_seconds=122,
        )
