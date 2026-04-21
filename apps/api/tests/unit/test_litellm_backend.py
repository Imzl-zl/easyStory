from __future__ import annotations

import asyncio

import litellm
import pytest

from app.shared.runtime.errors import (
    ConfigurationError,
    UpstreamRateLimitError,
    UpstreamServiceError,
)
from app.shared.runtime.llm.interop.provider_interop_stream_support import StreamInterruptedError
from app.shared.runtime.llm.llm_tool_provider import LLMToolProvider
from app.shared.runtime.llm.interop.provider_tool_conformance_support import (
    build_text_probe_request,
)
from app.shared.runtime.llm.llm_backend import resolve_backend_selection
from app.shared.runtime.llm.litellm_backend import (
    LiteLLMBackend,
    _execute_litellm_call,
    build_litellm_call_spec,
)
from app.shared.runtime.llm.llm_protocol_types import LLMConnection, LLMGenerateRequest


def test_build_litellm_call_spec_uses_openai_prefix_and_api_base_for_openai_compatible_gateway() -> (
    None
):
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


def test_build_litellm_call_spec_appends_gemini_models_path_for_root_gateway() -> None:
    request = LLMGenerateRequest(
        connection=LLMConnection(
            provider="gemini",
            api_dialect="gemini_generate_content",
            api_key="test-key",
            base_url="https://proxy.example.com",
        ),
        model_name="gemini-flash-latest",
        prompt="hi",
        system_prompt=None,
        response_format="text",
        temperature=0.0,
        max_tokens=32,
        top_p=1.0,
        thinking_budget=0,
    )

    spec = build_litellm_call_spec(request)

    assert spec.call_kwargs["api_base"] == "https://proxy.example.com/v1beta/models"


def test_build_litellm_call_spec_keeps_explicit_gemini_models_path() -> None:
    request = LLMGenerateRequest(
        connection=LLMConnection(
            provider="gemini",
            api_dialect="gemini_generate_content",
            api_key="test-key",
            base_url="https://proxy.example.com/v1beta/models",
        ),
        model_name="gemini-flash-latest",
        prompt="hi",
        system_prompt=None,
        response_format="text",
        temperature=0.0,
        max_tokens=32,
        top_p=1.0,
        thinking_budget=0,
    )

    spec = build_litellm_call_spec(request)

    assert spec.call_kwargs["api_base"] == "https://proxy.example.com/v1beta/models"


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
        return FakeStream(
            [
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
            ]
        )

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
        return FakeStream(
            [
                {
                    "type": "response.failed",
                    "response": {"error": {"message": "上游失败"}},
                }
            ]
        )

    monkeypatch.setattr(litellm, "aresponses", fake_aresponses)
    backend = LiteLLMBackend()

    async def collect():
        events = []
        async for event in backend.generate_stream(request):
            events.append(event)
        return events

    with pytest.raises(ConfigurationError, match="上游失败"):
        asyncio.run(collect())


def test_litellm_backend_generate_parses_responses_bridge_payload_as_openai_chat(
    monkeypatch,
) -> None:
    request = build_text_probe_request(
        LLMConnection(
            provider="openai",
            api_dialect="openai_responses",
            api_key="test-key",
            base_url="https://api.openai.com/v1",
        ),
        model_name="gpt-4.1-mini",
    )

    async def fake_aresponses(**kwargs):
        return {
            "choices": [{"message": {"content": "bridge 文本"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }

    monkeypatch.setattr(litellm, "aresponses", fake_aresponses)

    normalized = asyncio.run(LiteLLMBackend().generate(request))

    assert normalized.content == "bridge 文本"
    assert normalized.finish_reason == "stop"


def test_litellm_backend_generate_stream_parses_responses_bridge_chunks_as_openai_chat(
    monkeypatch,
) -> None:
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
        return FakeStream(
            [
                {"choices": [{"delta": {"content": "bridge "}, "finish_reason": None}]},
                {"choices": [{"delta": {"content": "stream"}, "finish_reason": None}]},
                {"choices": [{"delta": {}, "finish_reason": "stop"}]},
            ]
        )

    monkeypatch.setattr(litellm, "aresponses", fake_aresponses)
    backend = LiteLLMBackend()

    async def collect():
        events = []
        async for event in backend.generate_stream(request):
            events.append(event)
        return events

    events = asyncio.run(collect())

    assert [event.delta for event in events[:-1]] == ["bridge ", "stream"]
    assert events[-1].terminal_response is not None
    assert events[-1].terminal_response.content == "bridge stream"


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


def test_litellm_backend_generate_stream_preserves_interrupt_semantics_when_close_fails(
    monkeypatch,
) -> None:
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
        def __init__(self) -> None:
            self.closed = False
            self._yielded = False

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self._yielded:
                raise StopAsyncIteration
            self._yielded = True
            return {"type": "response.output_text.delta", "delta": "忽略"}

        async def aclose(self) -> None:
            self.closed = True
            raise RuntimeError("close failed")

    stream = FakeStream()

    async def fake_aresponses(**kwargs):
        return stream

    monkeypatch.setattr(litellm, "aresponses", fake_aresponses)
    backend = LiteLLMBackend()

    async def should_stop() -> bool:
        return True

    async def collect():
        events = []
        async for event in backend.generate_stream(
            request,
            should_stop=should_stop,
        ):
            events.append(event)
        return events

    with pytest.raises(
        StreamInterruptedError, match="Client disconnected during streaming"
    ) as exc_info:
        asyncio.run(collect())

    assert stream.closed is True
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert str(exc_info.value.__cause__) == "close failed"


def test_litellm_backend_maps_rate_limit_error_to_specific_exception(monkeypatch) -> None:
    request = build_text_probe_request(
        LLMConnection(
            provider="openai",
            api_dialect="openai_chat_completions",
            api_key="test-key",
            base_url="https://api.openai.com/v1",
        ),
        model_name="gpt-4.1-mini",
    )

    async def fake_acompletion(**kwargs):
        raise litellm.RateLimitError(
            message="too many requests",
            llm_provider="openai",
            model="gpt-4.1-mini",
        )

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    with pytest.raises(UpstreamRateLimitError, match="too many requests"):
        asyncio.run(LiteLLMBackend().generate(request))


def test_litellm_backend_maps_generic_api_error_to_upstream_service_error(monkeypatch) -> None:
    request = build_text_probe_request(
        LLMConnection(
            provider="openai",
            api_dialect="openai_chat_completions",
            api_key="test-key",
            base_url="https://api.openai.com/v1",
        ),
        model_name="gpt-4.1-mini",
    )

    async def fake_acompletion(**kwargs):
        raise litellm.APIError(
            status_code=503,
            message="gateway exploded",
            llm_provider="openai",
            model="gpt-4.1-mini",
        )

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    with pytest.raises(UpstreamServiceError, match="gateway exploded"):
        asyncio.run(LiteLLMBackend().generate(request))


def test_litellm_backend_keeps_bad_request_as_configuration_error(monkeypatch) -> None:
    request = build_text_probe_request(
        LLMConnection(
            provider="openai",
            api_dialect="openai_chat_completions",
            api_key="test-key",
            base_url="https://api.openai.com/v1",
        ),
        model_name="gpt-4.1-mini",
    )

    async def fake_acompletion(**kwargs):
        raise litellm.BadRequestError(
            message="bad payload",
            llm_provider="openai",
            model="gpt-4.1-mini",
        )

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    with pytest.raises(ConfigurationError, match="bad payload"):
        asyncio.run(LiteLLMBackend().generate(request))


def test_execute_litellm_call_rejects_unknown_call_kind() -> None:
    with pytest.raises(ConfigurationError, match="Unsupported LiteLLM call kind"):
        asyncio.run(
            _execute_litellm_call(
                call_kind="unknown",  # type: ignore[arg-type]
                call_kwargs={},
            )
        )


def test_build_litellm_call_spec_keeps_existing_openai_prefix_for_openai_compatible_gateway() -> (
    None
):
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
