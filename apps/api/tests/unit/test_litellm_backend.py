from __future__ import annotations

import asyncio

import litellm
import pytest

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.llm_tool_provider import LLMToolProvider
from app.shared.runtime.llm.interop.provider_tool_conformance_support import build_text_probe_request
from app.shared.runtime.llm.llm_backend import resolve_backend_selection
from app.shared.runtime.llm.litellm_backend import LiteLLMBackend, build_litellm_call_spec
from app.shared.runtime.llm.llm_protocol_types import LLMConnection, LLMGenerateRequest


def test_build_litellm_call_spec_uses_openai_prefix_and_api_base_for_openai_compatible_gateway() -> None:
    request = LLMGenerateRequest(
        connection=LLMConnection(
            provider="deepseek",
            api_dialect="openai_chat_completions",
            api_key="test-key",
            base_url="https://proxy.example.com/v1",
        ),
        model_name="deepseek-chat",
        prompt="hi",
        system_prompt=None,
        response_format="text",
        temperature=0.0,
        max_tokens=32,
        top_p=1.0,
    )

    spec = build_litellm_call_spec(request)

    assert spec.call_kind == "completion"
    assert spec.call_kwargs["model"] == "openai/deepseek-chat"
    assert spec.call_kwargs["api_base"] == "https://proxy.example.com/v1"
    assert spec.call_kwargs["custom_llm_provider"] == "openai"


def test_build_litellm_call_spec_keeps_openai_model_for_official_openai() -> None:
    request = build_text_probe_request(
        LLMConnection(
            provider="openai",
            api_dialect="openai_chat_completions",
            api_key="test-key",
            base_url="https://api.openai.com",
        ),
        model_name="gpt-4.1-mini",
    )

    spec = build_litellm_call_spec(request)

    assert spec.call_kwargs["model"] == "gpt-4.1-mini"
    assert "api_base" not in spec.call_kwargs


def test_resolve_backend_selection_uses_native_for_full_endpoint_base_url() -> None:
    request = build_text_probe_request(
        LLMConnection(
            api_dialect="openai_chat_completions",
            api_key="test-key",
            base_url="https://proxy.example.com/v1/chat/completions",
        ),
        model_name="gpt-4.1-mini",
    )

    selection = resolve_backend_selection(request)

    assert selection.backend_key == "native_http"

def test_llm_tool_provider_defaults_to_litellm_backend_for_openai_chat(monkeypatch) -> None:
    captured = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        return {
            "choices": [{"message": {"content": "生成结果"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
    provider = LLMToolProvider()

    result = asyncio.run(
        provider.execute(
            "llm.generate",
            {
                "prompt": "测试提示词",
                "model": {"provider": "openai", "name": "gpt-4.1-mini"},
                "credential": {"api_key": "test-key", "api_dialect": "openai_chat_completions"},
            },
        )
    )

    assert captured["model"] == "gpt-4.1-mini"
    assert result["content"] == "生成结果"


def test_build_litellm_call_spec_uses_openai_prefix_for_openai_responses_gateway() -> None:
    request = LLMGenerateRequest(
        connection=LLMConnection(
            provider="deepseek",
            api_dialect="openai_responses",
            api_key="test-key",
            base_url="https://proxy.example.com/v1",
        ),
        model_name="deepseek-reasoner",
        prompt="hi",
        system_prompt=None,
        response_format="text",
        temperature=0.0,
        max_tokens=32,
        top_p=1.0,
    )

    spec = build_litellm_call_spec(request)

    assert spec.call_kind == "responses"
    assert spec.call_kwargs["model"] == "openai/deepseek-reasoner"
    assert spec.call_kwargs["api_base"] == "https://proxy.example.com/v1"
    assert spec.call_kwargs["custom_llm_provider"] == "openai"


def test_resolve_backend_selection_uses_native_for_openai_responses_stop() -> None:
    request = LLMGenerateRequest(
        connection=LLMConnection(
            api_dialect="openai_responses",
            api_key="test-key",
            base_url="https://api.openai.com/v1",
        ),
        model_name="gpt-4.1-mini",
        prompt="hi",
        system_prompt=None,
        response_format="text",
        temperature=0.0,
        max_tokens=32,
        top_p=1.0,
        stop=["END"],
    )

    selection = resolve_backend_selection(request)

    assert selection.backend_key == "native_http"


def test_resolve_backend_selection_keeps_gemini_zero_budget_on_litellm() -> None:
    request = LLMGenerateRequest(
        connection=LLMConnection(
            provider="gemini",
            api_dialect="gemini_generate_content",
            api_key="test-key",
            base_url="https://generativelanguage.googleapis.com",
        ),
        model_name="gemini-2.5-flash",
        prompt="hi",
        system_prompt=None,
        response_format="text",
        temperature=0.0,
        max_tokens=32,
        top_p=1.0,
        thinking_budget=0,
    )

    selection = resolve_backend_selection(request)

    assert selection.backend_key == "litellm"


def test_resolve_backend_selection_uses_native_for_nonzero_gemini_budget() -> None:
    request = LLMGenerateRequest(
        connection=LLMConnection(
            provider="gemini",
            api_dialect="gemini_generate_content",
            api_key="test-key",
            base_url="https://generativelanguage.googleapis.com",
        ),
        model_name="gemini-2.5-flash",
        prompt="hi",
        system_prompt=None,
        response_format="text",
        temperature=0.0,
        max_tokens=32,
        top_p=1.0,
        thinking_budget=64,
    )

    selection = resolve_backend_selection(request)

    assert selection.backend_key == "native_http"


def test_litellm_backend_generate_stream_accepts_responses_incomplete_terminal(monkeypatch) -> None:
    request = build_text_probe_request(
        LLMConnection(
            provider="openai",
            api_dialect="openai_responses",
            api_key="test-key",
            base_url="https://api.openai.com/v1",
        ),
        model_name="gpt-4.1-mini",
    )

    class FakeStream:
        def __init__(self, events):
            self._events = list(events)

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self._events:
                raise StopAsyncIteration
            return self._events.pop(0)

    async def fake_aresponses(**kwargs):
        return FakeStream([
            {
                "type": "response.incomplete",
                "response": {
                    "id": "resp_123",
                    "output": [
                        {
                            "id": "msg_1",
                            "type": "message",
                            "content": [{"type": "output_text", "text": "半截内容"}],
                        }
                    ],
                    "incomplete_details": {"reason": "content_filter"},
                },
            }
        ])

    monkeypatch.setattr(litellm, "aresponses", fake_aresponses)
    backend = LiteLLMBackend()

    async def collect():
        events = []
        async for event in backend.generate_stream(request):
            events.append(event)
        return events

    events = asyncio.run(collect())

    assert len(events) == 1
    assert events[0].terminal_response is not None
    assert events[0].terminal_response.content == "半截内容"
    assert events[0].terminal_response.finish_reason == "content_filter"


def test_litellm_backend_generate_stream_raises_responses_failed_message(monkeypatch) -> None:
    request = build_text_probe_request(
        LLMConnection(
            provider="openai",
            api_dialect="openai_responses",
            api_key="test-key",
            base_url="https://api.openai.com/v1",
        ),
        model_name="gpt-4.1-mini",
    )

    class FakeStream:
        def __init__(self, events):
            self._events = list(events)

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self._events:
                raise StopAsyncIteration
            return self._events.pop(0)

    async def fake_aresponses(**kwargs):
        return FakeStream([
            {
                "type": "response.failed",
                "response": {"error": {"message": "上游失败"}},
            }
        ])

    monkeypatch.setattr(litellm, "aresponses", fake_aresponses)
    backend = LiteLLMBackend()

    async def collect():
        events = []
        async for event in backend.generate_stream(request):
            events.append(event)
        return events

    with pytest.raises(ConfigurationError, match="上游失败"):
        asyncio.run(collect())


def test_resolve_backend_selection_uses_native_for_gemini_stream_endpoint() -> None:
    request = build_text_probe_request(
        LLMConnection(
            provider="gemini",
            api_dialect="gemini_generate_content",
            api_key="test-key",
            base_url=(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                "gemini-2.5-flash:streamGenerateContent"
            ),
        ),
        model_name="gemini-2.5-flash",
    )

    selection = resolve_backend_selection(request)

    assert selection.backend_key == "native_http"


def test_litellm_backend_generate_stream_keeps_local_configuration_errors(monkeypatch) -> None:
    request = build_text_probe_request(
        LLMConnection(
            provider="openai",
            api_dialect="openai_responses",
            api_key="test-key",
            base_url="https://api.openai.com/v1",
        ),
        model_name="gpt-4.1-mini",
    )

    class FakeStream:
        def __init__(self, events):
            self._events = list(events)

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self._events:
                raise StopAsyncIteration
            return self._events.pop(0)

    async def fake_aresponses(**kwargs):
        return FakeStream([object()])

    monkeypatch.setattr(litellm, "aresponses", fake_aresponses)
    backend = LiteLLMBackend()

    async def collect():
        events = []
        async for event in backend.generate_stream(request):
            events.append(event)
        return events

    with pytest.raises(ConfigurationError, match="unsupported payload object"):
        asyncio.run(collect())


def test_build_litellm_call_spec_keeps_existing_openai_prefix_for_openai_compatible_gateway() -> None:
    request = LLMGenerateRequest(
        connection=LLMConnection(
            provider="deepseek",
            api_dialect="openai_chat_completions",
            api_key="test-key",
            base_url="https://proxy.example.com/v1",
        ),
        model_name="openai/deepseek-chat",
        prompt="hi",
        system_prompt=None,
        response_format="text",
        temperature=0.0,
        max_tokens=32,
        top_p=1.0,
    )

    spec = build_litellm_call_spec(request)

    assert spec.call_kwargs["model"] == "openai/deepseek-chat"
