from __future__ import annotations

from collections.abc import Callable
import asyncio

import httpx
import pytest

from app.modules.credential.infrastructure import AsyncHttpCredentialVerifier
from app.shared.runtime.errors import (
    BusinessRuleError,
    ConfigurationError,
    UpstreamAuthenticationError,
)
from app.shared.runtime.llm.llm_backend import LLMBackendStreamEvent
from app.shared.runtime.llm.llm_protocol_types import (
    LLMGenerateRequest,
    NormalizedLLMResponse,
    PreparedLLMHttpRequest,
    VERIFY_SYSTEM_PROMPT,
    VERIFY_USER_PROMPT,
)
from app.shared.runtime.llm.llm_protocol_types import NormalizedLLMToolCall
from app.shared.settings import (
    ALLOW_INSECURE_PUBLIC_MODEL_ENDPOINTS_ENV,
    ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV,
    clear_settings_cache,
)


class RecordingBackend:
    def __init__(
        self,
        *,
        generate_results: list[NormalizedLLMResponse | Exception | Callable[[LLMGenerateRequest], NormalizedLLMResponse]] | None = None,
        stream_sequences: list[list[LLMBackendStreamEvent] | Exception | Callable[[LLMGenerateRequest], list[LLMBackendStreamEvent]]] | None = None,
    ) -> None:
        self.generate_results = list(generate_results or [])
        self.stream_sequences = list(stream_sequences or [])
        self.generate_requests: list[LLMGenerateRequest] = []
        self.stream_requests: list[LLMGenerateRequest] = []

    async def generate(self, request: LLMGenerateRequest) -> NormalizedLLMResponse:
        self.generate_requests.append(request)
        if not self.generate_results:
            raise AssertionError("unexpected generate call")
        result = self.generate_results.pop(0)
        if isinstance(result, Exception):
            raise result
        if callable(result):
            return result(request)
        return result

    async def generate_stream(self, request: LLMGenerateRequest, *, should_stop=None):
        self.stream_requests.append(request)
        if not self.stream_sequences:
            raise AssertionError("unexpected generate_stream call")
        sequence = self.stream_sequences.pop(0)
        if isinstance(sequence, Exception):
            raise sequence
        if callable(sequence):
            sequence = sequence(request)
        for event in sequence:
            yield event


def _ok_response(
    content: str,
    *,
    input_tokens: int = 1,
    output_tokens: int = 1,
    total_tokens: int = 2,
) -> NormalizedLLMResponse:
    return NormalizedLLMResponse(
        content=content,
        finish_reason=None,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


def test_verify_credential_uses_native_stream_backend_request_for_custom_header() -> None:
    litellm_backend = RecordingBackend()
    native_backend = RecordingBackend(
        stream_sequences=[[LLMBackendStreamEvent(terminal_response=_ok_response("今天天气真好。"))]],
    )

    verifier = AsyncHttpCredentialVerifier(
        litellm_backend=litellm_backend,
        native_backend=native_backend,
    )
    result = asyncio.run(
        verifier.verify(
            provider="openai",
            api_key="test-key",
            base_url="https://proxy.example.com",
            api_dialect="openai_chat_completions",
            default_model="gpt-4o-mini",
            interop_profile="chat_compat_reasoning_content",
            auth_strategy="custom_header",
            api_key_header_name="api-key",
            extra_headers={"X-Trace-Id": "trace-verify"},
            user_agent_override=None,
            client_name="easyStory",
            client_version="0.1",
            runtime_kind="server-python",
        )
    )

    request = native_backend.stream_requests[0]
    assert request.model_name == "gpt-4o-mini"
    assert request.prompt == VERIFY_USER_PROMPT
    assert request.system_prompt == VERIFY_SYSTEM_PROMPT
    assert request.connection.api_key == "test-key"
    assert request.connection.api_key_header_name == "api-key"
    assert request.connection.extra_headers == {"X-Trace-Id": "trace-verify"}
    assert request.connection.client_name == "easyStory"
    assert request.connection.client_version == "0.1"
    assert request.connection.runtime_kind == "server-python"
    assert request.force_tool_call is False
    assert litellm_backend.generate_requests == []
    assert litellm_backend.stream_requests == []
    assert result.message == "验证成功"
    assert result.probe_kind == "text_probe"


def test_verify_credential_accepts_non_exact_probe_reply() -> None:
    backend = RecordingBackend(
        stream_sequences=[[LLMBackendStreamEvent(terminal_response=_ok_response("今天天气真好。\n补充一句说明也没关系。"))]],
    )

    verifier = AsyncHttpCredentialVerifier(backend=backend)
    result = asyncio.run(
        verifier.verify(
            provider="openai",
            api_key="test-key",
            base_url=None,
            api_dialect="openai_chat_completions",
            default_model="gpt-4o-mini",
            client_name="easyStory",
        )
    )

    assert result.message == "验证成功"


def test_verify_credential_text_probe_requires_terminal_response_after_stream_delta() -> None:
    backend = RecordingBackend(
        stream_sequences=[[LLMBackendStreamEvent(delta="我")]],
    )

    verifier = AsyncHttpCredentialVerifier(backend=backend)

    with pytest.raises(BusinessRuleError, match="Streaming backend completed without terminal response"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url="https://proxy.example.com",
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
                client_name="easyStory",
            )
        )


def test_verify_credential_text_probe_waits_for_terminal_response_after_delta() -> None:
    backend = RecordingBackend(
        stream_sequences=[[
            LLMBackendStreamEvent(delta="我"),
            LLMBackendStreamEvent(terminal_response=_ok_response("今天天气真好。")),
        ]],
    )

    verifier = AsyncHttpCredentialVerifier(backend=backend)
    result = asyncio.run(
        verifier.verify(
            provider="openai",
            api_key="test-key",
            base_url="https://proxy.example.com",
            api_dialect="openai_chat_completions",
            default_model="gpt-4o-mini",
            client_name="easyStory",
        )
    )

    assert result.message == "验证成功"
    assert result.probe_kind == "text_probe"


def test_verify_credential_text_probe_accepts_terminal_response_without_delta() -> None:
    backend = RecordingBackend(
        stream_sequences=[[LLMBackendStreamEvent(terminal_response=_ok_response("今天天气真好。"))]],
    )

    verifier = AsyncHttpCredentialVerifier(backend=backend)
    result = asyncio.run(
        verifier.verify(
            provider="openai",
            api_key="test-key",
            base_url="https://proxy.example.com",
            api_dialect="openai_responses",
            default_model="gpt-4.1-mini",
            client_name="easyStory",
        )
    )

    assert result.message == "验证成功"
    assert result.probe_kind == "text_probe"


def test_verify_credential_text_probe_uses_buffered_backend_for_anthropic() -> None:
    litellm_backend = RecordingBackend(generate_results=[_ok_response("今天天气真好。")])
    native_backend = RecordingBackend()

    verifier = AsyncHttpCredentialVerifier(
        litellm_backend=litellm_backend,
        native_backend=native_backend,
    )
    result = asyncio.run(
        verifier.verify(
            provider="claude",
            api_key="test-key",
            base_url="https://proxy.example.com",
            api_dialect="anthropic_messages",
            default_model="claude-sonnet-4-6",
            client_name="easyStory",
        )
    )

    assert len(litellm_backend.generate_requests) == 1
    assert litellm_backend.stream_requests == []
    assert result.message == "验证成功"
    assert result.probe_kind == "text_probe"


def test_verify_credential_rejects_empty_probe_content() -> None:
    backend = RecordingBackend(
        stream_sequences=[[LLMBackendStreamEvent(terminal_response=_ok_response("   "))]],
    )

    verifier = AsyncHttpCredentialVerifier(backend=backend)

    with pytest.raises(BusinessRuleError, match="测试消息没有返回可用内容"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url=None,
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
                user_agent_override=None,
                client_name="easyStory",
            )
        )


def test_verify_credential_rejects_retired_model_message() -> None:
    backend = RecordingBackend(
        stream_sequences=[[
            LLMBackendStreamEvent(
                terminal_response=_ok_response(
                    "Gemini 3 Pro is no longer available. Please switch to Gemini 3.1 Pro."
                )
            )
        ]],
    )

    verifier = AsyncHttpCredentialVerifier(backend=backend)

    with pytest.raises(BusinessRuleError, match="当前默认模型已不可用"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url=None,
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
                user_agent_override=None,
                client_name="easyStory",
            )
        )


def test_verify_credential_rejects_model_configuration_error_message() -> None:
    backend = RecordingBackend(
        stream_sequences=[[
            LLMBackendStreamEvent(
                terminal_response=_ok_response("MEDIUM is not supported for this model.")
            )
        ]],
    )

    verifier = AsyncHttpCredentialVerifier(backend=backend)

    with pytest.raises(BusinessRuleError, match="默认模型或接口类型不匹配"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url=None,
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
                user_agent_override=None,
                client_name="easyStory",
            )
        )


def test_verify_credential_surfaces_stream_protocol_error() -> None:
    backend = RecordingBackend(
        stream_sequences=[ConfigurationError("模型没有返回可展示的内容，请稍后重试。")],
    )

    verifier = AsyncHttpCredentialVerifier(backend=backend)

    with pytest.raises(BusinessRuleError, match="模型没有返回可展示的内容，请稍后重试"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url=None,
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
                user_agent_override=None,
                client_name="easyStory",
            )
        )


def test_verify_credential_surfaces_empty_tool_response_protocol_error() -> None:
    backend = RecordingBackend(
        stream_sequences=[ConfigurationError(
            "当前连接在启用工具时返回了空响应：既没有文本，也没有工具调用。"
            "这通常表示该连接当前不支持所选协议下的工具调用。"
            "请重新执行“验证工具”，或切换可稳定支持工具调用的连接。"
        )],
    )

    verifier = AsyncHttpCredentialVerifier(backend=backend)

    with pytest.raises(BusinessRuleError, match="启用工具时返回了空响应"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url=None,
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
                probe_kind="tool_continuation_probe",
                transport_mode="stream",
                user_agent_override=None,
                client_name="easyStory",
            )
        )


def test_verify_tool_continuation_probe_replays_followup_request() -> None:
    backend = RecordingBackend(
        stream_sequences=[
            [LLMBackendStreamEvent(terminal_response=_tool_call_response(provider_response_id="resp_123"))],
            lambda request: [
                LLMBackendStreamEvent(
                    terminal_response=_ok_response(
                        f"工具续接成功：{request.continuation_items[-1]['payload']['echoed']}"
                    )
                )
            ],
        ],
    )

    verifier = AsyncHttpCredentialVerifier(backend=backend)

    result = asyncio.run(
        verifier.verify(
            provider="openai",
            api_key="test-key",
            base_url="https://proxy.example.com",
            api_dialect="openai_responses",
            default_model="gpt-5.4",
            probe_kind="tool_continuation_probe",
            transport_mode="stream",
            client_name="easyStory",
        )
    )

    assert len(backend.stream_requests) == 2
    assert backend.stream_requests[0].force_tool_call is True
    assert backend.stream_requests[0].tools[0].name == "probe.echo_payload"
    assert backend.stream_requests[1].force_tool_call is False
    assert backend.stream_requests[1].provider_continuation_state is None
    tool_result_payload = backend.stream_requests[1].continuation_items[-1]["payload"]
    assert tool_result_payload["echoed"].startswith("probe-result-")
    assert tool_result_payload["echoed"] != "ping"
    assert result.message == "流式工具调用验证成功"
    assert result.probe_kind == "tool_continuation_probe"
    assert result.transport_mode == "stream"


def test_verify_tool_probe_requires_transport_mode() -> None:
    verifier = AsyncHttpCredentialVerifier()

    with pytest.raises(BusinessRuleError, match="工具验证必须显式指定 transport_mode"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url=None,
                api_dialect="openai_responses",
                default_model="gpt-5.4",
                probe_kind="tool_continuation_probe",
            )
        )


def test_verify_text_probe_accepts_explicit_stream_transport_mode() -> None:
    captured: dict[str, object] = {}

    async def stream_request_sender(request, *, api_dialect):
        captured["request"] = request
        captured["api_dialect"] = api_dialect
        return _ok_response("今天天气真好。")

    verifier = AsyncHttpCredentialVerifier(stream_request_sender=stream_request_sender)
    result = asyncio.run(
        verifier.verify(
            provider="claude",
            api_key="test-key",
            base_url="https://proxy.example.com",
            api_dialect="anthropic_messages",
            default_model="claude-sonnet-4-6",
            transport_mode="stream",
        )
    )

    request = captured["request"]
    assert request.headers["Accept"] == "text/event-stream"
    assert request.json_body["stream"] is True
    assert captured["api_dialect"] == "anthropic_messages"
    assert result.message == "流式连接验证成功"
    assert result.transport_mode == "stream"


def test_verify_buffered_tool_probe_uses_generate_backend() -> None:
    backend = RecordingBackend(
        generate_results=[
            _tool_call_response(provider_response_id="resp_123"),
            lambda request: _ok_response(
                f"工具续接成功：{request.continuation_items[-1]['payload']['echoed']}"
            ),
        ],
    )

    verifier = AsyncHttpCredentialVerifier(backend=backend)
    result = asyncio.run(
        verifier.verify(
            provider="openai",
            api_key="test-key",
            base_url="https://proxy.example.com",
            api_dialect="openai_responses",
            default_model="gpt-5.4",
            probe_kind="tool_continuation_probe",
            transport_mode="buffered",
            client_name="easyStory",
        )
    )

    assert len(backend.generate_requests) == 2
    assert backend.stream_requests == []
    assert backend.generate_requests[0].force_tool_call is True
    assert backend.generate_requests[1].force_tool_call is False
    assert result.message == "非流工具调用验证成功"
    assert result.probe_kind == "tool_continuation_probe"
    assert result.transport_mode == "buffered"


def test_verify_credential_maps_authentication_error() -> None:
    backend = RecordingBackend(
        stream_sequences=[ConfigurationError("LLM streaming request failed: HTTP 401 - bad key")],
    )

    verifier = AsyncHttpCredentialVerifier(backend=backend)

    with pytest.raises(BusinessRuleError, match="API Key 无效"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url=None,
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
                client_name="easyStory",
            )
        )


def test_verify_credential_maps_upstream_authentication_error_subclass() -> None:
    backend = RecordingBackend(
        stream_sequences=[UpstreamAuthenticationError("LLM streaming request failed: HTTP 401 - bad key")],
    )

    verifier = AsyncHttpCredentialVerifier(backend=backend)

    with pytest.raises(BusinessRuleError, match="API Key 无效"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url=None,
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
                client_name="easyStory",
            )
        )


def test_verify_credential_surfaces_connection_error() -> None:
    async def stream_request_sender(_request, *, api_dialect):
        assert api_dialect == "openai_chat_completions"
        raise httpx.ConnectError("connect failed")

    verifier = AsyncHttpCredentialVerifier(stream_request_sender=stream_request_sender)

    with pytest.raises(BusinessRuleError, match="无法连接到 openai"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url=None,
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
                client_name="easyStory",
            )
        )


def test_verify_credential_requires_executable_model_name() -> None:
    verifier = AsyncHttpCredentialVerifier()

    with pytest.raises(BusinessRuleError, match="missing executable model name"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url=None,
                api_dialect="openai_chat_completions",
                default_model=None,
            )
        )


def test_verify_credential_rejects_private_base_url_by_default(monkeypatch) -> None:
    monkeypatch.setenv(ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV, "false")
    clear_settings_cache()
    verifier = AsyncHttpCredentialVerifier()

    with pytest.raises(BusinessRuleError, match="Private or local model endpoints are disabled"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url="http://127.0.0.1:11434/v1",
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
            )
        )


def test_verify_credential_rejects_public_http_base_url_by_default(monkeypatch) -> None:
    monkeypatch.setenv(ALLOW_INSECURE_PUBLIC_MODEL_ENDPOINTS_ENV, "false")
    clear_settings_cache()
    verifier = AsyncHttpCredentialVerifier()

    with pytest.raises(BusinessRuleError, match="Public http model endpoints are disabled"):
        asyncio.run(
            verifier.verify(
                provider="openai",
                api_key="test-key",
                base_url="http://49.234.21.84:3000/v1",
                api_dialect="openai_chat_completions",
                default_model="gpt-4o-mini",
            )
        )


def test_verify_credential_allows_private_base_url_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv(ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV, "true")
    clear_settings_cache()
    captured: dict[str, object] = {}

    async def stream_request_sender(request, *, api_dialect):
        captured["request"] = request
        captured["api_dialect"] = api_dialect
        return _ok_response("今天天气真好。")

    verifier = AsyncHttpCredentialVerifier(stream_request_sender=stream_request_sender)
    asyncio.run(
        verifier.verify(
            provider="openai",
            api_key="test-key",
            base_url="http://127.0.0.1:11434/v1",
            api_dialect="openai_chat_completions",
            default_model="gpt-4o-mini",
        )
    )

    request = captured["request"]
    assert isinstance(request, PreparedLLMHttpRequest)
    assert request.url == "http://127.0.0.1:11434/v1/chat/completions"
    assert request.json_body["stream"] is True
    assert captured["api_dialect"] == "openai_chat_completions"


def test_verify_credential_allows_public_http_base_url_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv(ALLOW_INSECURE_PUBLIC_MODEL_ENDPOINTS_ENV, "true")
    clear_settings_cache()
    captured: dict[str, object] = {}

    async def stream_request_sender(request, *, api_dialect):
        captured["request"] = request
        captured["api_dialect"] = api_dialect
        return _ok_response("今天天气真好。")

    verifier = AsyncHttpCredentialVerifier(stream_request_sender=stream_request_sender)
    asyncio.run(
        verifier.verify(
            provider="openai",
            api_key="test-key",
            base_url="http://49.234.21.84:3000/v1",
            api_dialect="openai_chat_completions",
            default_model="gpt-4o-mini",
        )
    )

    request = captured["request"]
    assert isinstance(request, PreparedLLMHttpRequest)
    assert request.url == "http://49.234.21.84:3000/v1/chat/completions"
    assert request.json_body["stream"] is True
    assert captured["api_dialect"] == "openai_chat_completions"


def _tool_call_response(
    *,
    provider_response_id: str | None,
    arguments: dict[str, object] | None = None,
) -> NormalizedLLMResponse:
    return NormalizedLLMResponse(
        content="",
        finish_reason=None,
        input_tokens=8,
        output_tokens=10,
        total_tokens=18,
        provider_response_id=provider_response_id,
        tool_calls=[
            NormalizedLLMToolCall(
                tool_call_id="call_123",
                tool_name="probe.echo_payload",
                arguments=arguments or {"echo": "ping"},
                arguments_text='{"echo":"ping"}',
            )
        ],
    )
