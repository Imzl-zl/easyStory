from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.interop.provider_interop_support import ResolvedProviderInteropProfile
from app.shared.runtime.llm.interop.provider_tool_conformance_support import build_text_probe_request
from app.shared.runtime.llm.llm_backend import LLMBackendStreamEvent
from app.shared.runtime.llm.llm_protocol_types import LLMConnection, NormalizedLLMResponse
from scripts import provider_interop_check as provider_interop_check_module
from scripts.provider_interop_check import _execute_probe_request, _probe_text_profile, _render_staged_request, build_parser


def test_probe_parser_defaults_to_auto_transport() -> None:
    parser = build_parser()

    args = parser.parse_args(["probe", "gpt"])

    assert args.stream is None
    assert args.probe_kind == "text_probe"


def test_probe_parser_allows_explicit_buffered_override() -> None:
    parser = build_parser()

    args = parser.parse_args(["probe", "gpt", "--buffered"])

    assert args.stream is False


def test_probe_parser_accepts_tool_continuation_probe_kind() -> None:
    parser = build_parser()

    args = parser.parse_args(["probe", "gpt", "--probe-kind", "tool_continuation_probe"])

    assert args.probe_kind == "tool_continuation_probe"


def test_render_staged_request_uses_llm_generate_request_for_litellm_backend() -> None:
    request = build_text_probe_request(
        LLMConnection(
            api_dialect="openai_chat_completions",
            api_key="test-key-1234",
            base_url="https://api.openai.com",
        ),
        model_name="gpt-5.4",
    )

    payload = json.loads(_render_staged_request("initial", request, stream=True))

    assert payload["backend"]["key"] == "litellm"
    assert payload["request"]["kind"] == "llm_generate_request"
    assert payload["request"]["litellm_preview"]["call_kind"] == "completion"
    assert payload["request"]["litellm_preview"]["call_kwargs"]["model"] == "gpt-5.4"
    assert payload["request"]["prompt"] == "今天天气怎么样？"


def test_render_staged_request_uses_prepared_http_request_for_native_backend() -> None:
    request = build_text_probe_request(
        LLMConnection(
            api_dialect="openai_chat_completions",
            api_key="test-key-1234",
            base_url="https://proxy.example.com/v1/chat/completions",
        ),
        model_name="gpt-5.4",
    )

    payload = json.loads(_render_staged_request("initial", request, stream=True))

    assert payload["backend"]["key"] == "native_http"
    assert payload["request"]["kind"] == "prepared_http_request"
    assert payload["request"]["url"].endswith("/v1/chat/completions")
    assert payload["request"]["headers"]["Authorization"] == "Bear...1234"


def test_execute_probe_request_text_probe_waits_for_stream_terminal(monkeypatch) -> None:
    request = build_text_probe_request(
        LLMConnection(
            api_dialect="openai_chat_completions",
            api_key="test-key",
            base_url="https://api.openai.com",
        ),
        model_name="gpt-5.4",
    )

    class FakeBackend:
        async def generate(self, request):
            raise AssertionError("unexpected buffered call")

        async def generate_stream(self, request, *, should_stop=None):
            yield LLMBackendStreamEvent(delta="我")
            raise ConfigurationError("LLM streaming request failed: 上游失败")

    monkeypatch.setattr(provider_interop_check_module, "_resolve_backend", lambda request: FakeBackend())

    with pytest.raises(ConfigurationError, match="上游失败"):
        asyncio.run(
            _execute_probe_request(
                request,
                probe_kind="text_probe",
                print_response=False,
                stream=True,
            )
        )


def test_probe_text_profile_auto_transport_reports_effective_stream(monkeypatch, capsys) -> None:
    resolved = ResolvedProviderInteropProfile(
        profile_id="anthropic",
        provider="anthropic",
        model_name="claude-sonnet-4",
        connection=LLMConnection(
            provider="anthropic",
            api_dialect="anthropic_messages",
            api_key="test-key",
            base_url="https://api.anthropic.com",
        ),
        max_requests_per_minute=None,
        notes=None,
    )
    captured: dict[str, object] = {}

    async def fake_execute_probe_request(request, *, probe_kind, print_response, stream):
        captured["stream"] = stream
        return NormalizedLLMResponse(
            content="今天天气真好。",
            finish_reason=None,
            input_tokens=1,
            output_tokens=1,
            total_tokens=2,
        )

    monkeypatch.setattr(provider_interop_check_module, "_execute_probe_request", fake_execute_probe_request)
    monkeypatch.setattr(provider_interop_check_module, "_enforce_rate_limit_if_needed", lambda args, resolved: None)

    args = SimpleNamespace(
        prompt=None,
        system_prompt=None,
        show_request=True,
        dry_run=False,
        print_response=False,
        stream=None,
        skip_rate_limit=True,
    )

    assert asyncio.run(_probe_text_profile(args, resolved)) == 0
    output = capsys.readouterr().out

    assert captured["stream"] is False
    assert '"stream": false' in output
    assert '"stream": null' not in output


def test_probe_text_profile_rejects_blank_content(monkeypatch) -> None:
    resolved = ResolvedProviderInteropProfile(
        profile_id="openai",
        provider="openai",
        model_name="gpt-5.4",
        connection=LLMConnection(
            provider="openai",
            api_dialect="openai_chat_completions",
            api_key="test-key",
            base_url="https://api.openai.com",
        ),
        max_requests_per_minute=None,
        notes=None,
    )

    async def fake_execute_probe_request(request, *, probe_kind, print_response, stream):
        return NormalizedLLMResponse(
            content="   ",
            finish_reason=None,
            input_tokens=1,
            output_tokens=1,
            total_tokens=2,
        )

    monkeypatch.setattr(provider_interop_check_module, "_execute_probe_request", fake_execute_probe_request)
    monkeypatch.setattr(provider_interop_check_module, "_enforce_rate_limit_if_needed", lambda args, resolved: None)

    args = SimpleNamespace(
        prompt=None,
        system_prompt=None,
        show_request=False,
        dry_run=False,
        print_response=False,
        stream=None,
        skip_rate_limit=True,
    )

    with pytest.raises(ConfigurationError, match="测试消息没有返回可用内容"):
        asyncio.run(_probe_text_profile(args, resolved))
