from __future__ import annotations

import asyncio

import pytest

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.llm_protocol import PreparedLLMHttpRequest
from app.shared.runtime.llm.interop import provider_interop_stream_support as stream_support


def test_build_stream_probe_request_sets_stream_flag_for_openai_responses() -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://proxy.example.com/v1/responses",
        headers={"Authorization": "Bearer test-key"},
        json_body={"model": "gpt-5.2-codex"},
    )

    streamed = stream_support.build_stream_probe_request(
        request,
        api_dialect="openai_responses",
    )

    assert streamed.url == "https://proxy.example.com/v1/responses"
    assert streamed.headers["Accept"] == "text/event-stream"
    assert streamed.json_body["stream"] is True


def test_build_stream_probe_request_switches_gemini_endpoint() -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://x666.me/v1beta/models/gemini-flash-latest:generateContent",
        headers={"x-goog-api-key": "test-key"},
        json_body={"contents": [{"parts": [{"text": "今天有什么新闻"}]}]},
    )

    streamed = stream_support.build_stream_probe_request(
        request,
        api_dialect="gemini_generate_content",
    )

    assert streamed.url == (
        "https://x666.me/v1beta/models/gemini-flash-latest:streamGenerateContent?alt=sse"
    )
    assert "stream" not in streamed.json_body


def test_execute_stream_probe_request_collects_openai_responses_text(monkeypatch) -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://proxy.example.com/v1/responses",
        headers={"Accept": "text/event-stream"},
        json_body={"model": "gpt-5.2-codex", "stream": True},
    )

    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: response.output_text.delta"
            yield 'data: {"delta":"今天"}'
            yield ""
            yield "event: response.output_text.delta"
            yield 'data: {"delta":"有新闻"}'
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)

    normalized = asyncio.run(
        stream_support.execute_stream_probe_request(
            request,
            api_dialect="openai_responses",
            print_response=False,
        )
    )

    assert normalized.content == "今天有新闻"


def test_execute_stream_probe_request_rejects_empty_tool_response(monkeypatch) -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://proxy.example.com/v1/chat/completions",
        headers={"Accept": "text/event-stream"},
        json_body={
            "model": "gpt-5.4",
            "stream": True,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "project_read_documents",
                        "parameters": {
                            "type": "object",
                            "properties": {"paths": {"type": "array"}},
                            "required": ["paths"],
                        },
                    },
                }
            ],
        },
    )

    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield 'data: {"id":"chatcmpl_123","choices":[{"delta":{"role":"assistant"},"finish_reason":null}]}'
            yield ""
            yield 'data: {"id":"chatcmpl_123","choices":[{"delta":{},"finish_reason":"stop"}]}'
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)

    with pytest.raises(ConfigurationError, match="启用工具时返回了空响应"):
        asyncio.run(
            stream_support.execute_stream_probe_request(
                request,
                api_dialect="openai_chat_completions",
                print_response=False,
            )
        )


def test_execute_stream_probe_request_preserves_gemini_tool_call_from_early_event(monkeypatch) -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://x666.me/v1beta/models/gemini-flash-latest:streamGenerateContent?alt=sse",
        headers={"Accept": "text/event-stream"},
        json_body={
            "contents": [{"role": "user", "parts": [{"text": "调用工具"}]}],
            "tools": [{"functionDeclarations": [{"name": "probe_echo_payload"}]}],
        },
        tool_name_aliases={"probe.echo_payload": "probe_echo_payload"},
    )

    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield (
                'data: {"candidates":[{"content":{"parts":[{"functionCall":{"name":"probe_echo_payload",'
                '"args":{"echo":"ping"},"id":"call_gemini_1"}}],"role":"model"},"index":0}],'
                '"usageMetadata":{"promptTokenCount":114,"candidatesTokenCount":18,"totalTokenCount":189},'
                '"responseId":"resp_gemini_1"}'
            )
            yield ""
            yield (
                'data: {"candidates":[{"content":{"parts":[{"text":""}],"role":"model"},'
                '"finishReason":"STOP","index":0}],"usageMetadata":{"promptTokenCount":114,'
                '"candidatesTokenCount":18,"totalTokenCount":189},"responseId":"resp_gemini_1"}'
            )
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)

    normalized = asyncio.run(
        stream_support.execute_stream_probe_request(
            request,
            api_dialect="gemini_generate_content",
            print_response=False,
        )
    )

    assert normalized.content == ""
    assert normalized.finish_reason == "STOP"
    assert len(normalized.tool_calls) == 1
    assert normalized.tool_calls[0].tool_name == "probe.echo_payload"
    assert normalized.tool_calls[0].arguments == {"echo": "ping"}


def test_execute_stream_probe_request_preserves_anthropic_tool_call_from_stream_events(
    monkeypatch,
) -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://2capi.com/v1/messages",
        headers={"Accept": "text/event-stream"},
        json_body={
            "model": "claude-haiku-4-5-20251001",
            "messages": [{"role": "user", "content": [{"type": "text", "text": "调用工具"}]}],
            "tools": [{"name": "probe_echo_payload"}],
        },
        tool_name_aliases={"probe.echo_payload": "probe_echo_payload"},
    )

    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: message_start"
            yield (
                'data: {"type":"message_start","message":{"id":"msg_123","usage":{"input_tokens":109,"output_tokens":0}}}'
            )
            yield ""
            yield "event: content_block_start"
            yield 'data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}'
            yield ""
            yield "event: content_block_delta"
            yield 'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"先调用工具。"}}'
            yield ""
            yield "event: content_block_start"
            yield (
                'data: {"type":"content_block_start","index":1,"content_block":{"type":"tool_use","id":"call_1","name":"probe_echo_payload","input":{}}}'
            )
            yield ""
            yield "event: content_block_delta"
            yield (
                'data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"{\\"echo\\":\\"ping\\"}"}}'
            )
            yield ""
            yield "event: message_delta"
            yield (
                'data: {"type":"message_delta","usage":{"input_tokens":109,"output_tokens":45},"delta":{"stop_reason":"tool_use"}}'
            )
            yield ""
            yield "event: message_stop"
            yield 'data: {"type":"message_stop"}'
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)

    normalized = asyncio.run(
        stream_support.execute_stream_probe_request(
            request,
            api_dialect="anthropic_messages",
            print_response=False,
        )
    )

    assert normalized.content == "先调用工具。"
    assert normalized.finish_reason == "tool_use"
    assert len(normalized.tool_calls) == 1
    assert normalized.tool_calls[0].tool_call_id == "call_1"
    assert normalized.tool_calls[0].tool_name == "probe.echo_payload"
    assert normalized.tool_calls[0].arguments == {"echo": "ping"}


def test_execute_stream_probe_request_ignores_openai_completed_payload(monkeypatch) -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://proxy.example.com/v1/responses",
        headers={"Accept": "text/event-stream"},
        json_body={"model": "gpt-5.2-codex", "stream": True},
    )

    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: response.output_text.delta"
            yield 'data: {"delta":"今天"}'
            yield ""
            yield "event: response.completed"
            yield 'data: {"output_text":"今天"}'
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)

    normalized = asyncio.run(
        stream_support.execute_stream_probe_request(
            request,
            api_dialect="openai_responses",
            print_response=False,
        )
    )

    assert normalized.content == "今天"
    assert normalized.input_tokens is None
    assert normalized.output_tokens is None
    assert normalized.total_tokens is None


def test_execute_stream_probe_request_reads_openai_completed_response_payload(monkeypatch) -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://proxy.example.com/v1/responses",
        headers={"Accept": "text/event-stream"},
        json_body={"model": "gpt-5.2-codex", "stream": True},
    )

    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: response.completed"
            yield (
                'data: {"type":"response.completed","response":{"output":[{"type":"message",'
                '"content":[{"type":"output_text","text":"今天有新闻"}]}],'
                '"usage":{"input_tokens":8,"output_tokens":10,"total_tokens":18}}}'
            )
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)

    normalized = asyncio.run(
        stream_support.execute_stream_probe_request(
            request,
            api_dialect="openai_responses",
            print_response=False,
        )
    )

    assert normalized.content == "今天有新闻"
    assert normalized.input_tokens == 8
    assert normalized.output_tokens == 10
    assert normalized.total_tokens == 18


def test_execute_stream_probe_request_accepts_openai_empty_output_when_deltas_exist(
    monkeypatch,
) -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://proxy.example.com/v1/responses",
        headers={"Accept": "text/event-stream"},
        json_body={"model": "gpt-5.2-codex", "stream": True},
    )

    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: response.output_text.delta"
            yield 'data: {"delta":"今天"}'
            yield ""
            yield "event: response.output_text.delta"
            yield 'data: {"delta":"有新闻"}'
            yield ""
            yield "event: response.completed"
            yield (
                'data: {"type":"response.completed","response":{"id":"resp_123","output":[],'
                '"usage":{"input_tokens":8,"output_tokens":10,"total_tokens":18}}}'
            )
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)

    normalized = asyncio.run(
        stream_support.execute_stream_probe_request(
            request,
            api_dialect="openai_responses",
            print_response=False,
        )
    )

    assert normalized.content == "今天有新闻"
    assert normalized.provider_response_id == "resp_123"
    assert normalized.input_tokens == 8
    assert normalized.output_tokens == 10
    assert normalized.total_tokens == 18
    assert normalized.provider_output_items == []


def test_execute_stream_probe_request_recovers_openai_responses_tool_calls_from_output_item_events(
    monkeypatch,
) -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://proxy.example.com/v1/responses",
        headers={"Accept": "text/event-stream"},
        json_body={"model": "gpt-5.2-codex", "stream": True},
        tool_name_aliases={"project.read_documents": "project_read_documents"},
    )

    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: response.output_item.done"
            yield (
                'data: {"type":"response.output_item.done","item":{"id":"fc_123","type":"function_call",'
                '"call_id":"call_123","name":"project_read_documents","arguments":"{\\"paths\\":[\\"设定/人物.md\\"]}"}}'
            )
            yield ""
            yield "event: response.completed"
            yield (
                'data: {"type":"response.completed","response":{"id":"resp_123","output":[],'
                '"usage":{"input_tokens":8,"output_tokens":10,"total_tokens":18}}}'
            )
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)

    normalized = asyncio.run(
        stream_support.execute_stream_probe_request(
            request,
            api_dialect="openai_responses",
            print_response=False,
        )
    )

    assert normalized.content == ""
    assert normalized.provider_response_id == "resp_123"
    assert normalized.tool_calls[0].tool_call_id == "call_123"
    assert normalized.tool_calls[0].tool_name == "project.read_documents"
    assert normalized.tool_calls[0].arguments == {"paths": ["设定/人物.md"]}


def test_execute_stream_probe_request_deduplicates_openai_responses_function_call_keys_and_keeps_output_order(
    monkeypatch,
) -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://proxy.example.com/v1/responses",
        headers={"Accept": "text/event-stream"},
        json_body={"model": "gpt-5.2-codex", "stream": True},
        tool_name_aliases={"project.read_documents": "project_read_documents"},
    )

    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: response.function_call_arguments.done"
            yield (
                'data: {"type":"response.function_call_arguments.done","call_id":"call_123","name":"project_read_documents",'
                '"arguments":"{\\"paths\\":[\\"设定/人物.md\\"]}","output_index":0}'
            )
            yield ""
            yield "event: response.output_item.done"
            yield (
                'data: {"type":"response.output_item.done","output_index":0,"item":{"id":"fc_123","type":"function_call",'
                '"call_id":"call_123","name":"project_read_documents","arguments":"{\\"paths\\":[\\"设定/人物.md\\"]}"}}'
            )
            yield ""
            yield "event: response.completed"
            yield (
                'data: {"type":"response.completed","response":{"id":"resp_123","output":[{"id":"rs_1","type":"reasoning","summary":[]}],'
                '"usage":{"input_tokens":8,"output_tokens":10,"total_tokens":18}}}'
            )
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)

    normalized = asyncio.run(
        stream_support.execute_stream_probe_request(
            request,
            api_dialect="openai_responses",
            print_response=False,
        )
    )

    assert len(normalized.tool_calls) == 1
    assert normalized.tool_calls[0].tool_call_id == "call_123"
    assert normalized.tool_calls[0].provider_ref == "fc_123"
    assert [item["item_type"] for item in normalized.provider_output_items] == [
        "tool_call",
        "reasoning",
    ]


def test_execute_stream_probe_request_preserves_openai_responses_output_order_for_multiple_missing_tool_calls(
    monkeypatch,
) -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://proxy.example.com/v1/responses",
        headers={"Accept": "text/event-stream"},
        json_body={"model": "gpt-5.4", "stream": True},
        tool_name_aliases={"project.read_documents": "project_read_documents"},
    )

    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: response.function_call_arguments.done"
            yield (
                'data: {"type":"response.function_call_arguments.done","item_id":"fc_1","call_id":"call_1",'
                '"name":"project_read_documents","arguments":"{\\"paths\\":[\\"设定/人物-1.md\\"]}","output_index":0}'
            )
            yield ""
            yield "event: response.function_call_arguments.done"
            yield (
                'data: {"type":"response.function_call_arguments.done","item_id":"fc_2","call_id":"call_2",'
                '"name":"project_read_documents","arguments":"{\\"paths\\":[\\"设定/人物-2.md\\"]}","output_index":2}'
            )
            yield ""
            yield "event: response.completed"
            yield (
                'data: {"type":"response.completed","response":{"id":"resp_456","output":[{"id":"msg_1","type":"message","role":"assistant",'
                '"content":[{"type":"output_text","text":"先看第一份，再补第二份。"}]},{"id":"rs_1","type":"reasoning","summary":[]}],'
                '"usage":{"input_tokens":8,"output_tokens":10,"total_tokens":18}}}'
            )
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)

    normalized = asyncio.run(
        stream_support.execute_stream_probe_request(
            request,
            api_dialect="openai_responses",
            print_response=False,
        )
    )

    assert [item["item_type"] for item in normalized.provider_output_items] == [
        "tool_call",
        "text",
        "tool_call",
        "reasoning",
    ]
    assert [
        item.get("provider_ref")
        for item in normalized.provider_output_items
        if item["item_type"] == "tool_call"
    ] == ["fc_1", "fc_2"]


def test_execute_stream_probe_request_recovers_openai_chat_tool_calls_from_delta_events(
    monkeypatch,
) -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://proxy.example.com/v1/chat/completions",
        headers={"Accept": "text/event-stream"},
        json_body={"model": "gpt-5.4", "stream": True},
        tool_name_aliases={"project.read_documents": "project_read_documents"},
    )

    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield (
                'data: {"id":"chatcmpl_123","choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_123",'
                '"type":"function","function":{"name":"project_read_documents","arguments":""}}],"role":"assistant"},'
                '"finish_reason":null}]}'
            )
            yield ""
            yield (
                'data: {"id":"chatcmpl_123","choices":[{"delta":{"tool_calls":[{"index":0,"function":'
                '{"arguments":"{\\"paths\\":[\\"设定/人物.md\\"]}"}}]},"finish_reason":null}]}'
            )
            yield ""
            yield 'data: {"id":"chatcmpl_123","choices":[{"delta":{},"finish_reason":"tool_calls"}]}'
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)

    normalized = asyncio.run(
        stream_support.execute_stream_probe_request(
            request,
            api_dialect="openai_chat_completions",
            print_response=False,
        )
    )

    assert normalized.content == ""
    assert normalized.finish_reason == "tool_calls"
    assert normalized.tool_calls[0].tool_call_id == "call_123"
    assert normalized.tool_calls[0].tool_name == "project.read_documents"
    assert normalized.tool_calls[0].arguments == {"paths": ["设定/人物.md"]}


def test_execute_stream_probe_request_rejects_openai_empty_output_when_strict_profile(
    monkeypatch,
) -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://proxy.example.com/v1/responses",
        headers={"Accept": "text/event-stream"},
        json_body={"model": "gpt-5.2-codex", "stream": True},
        interop_profile="responses_strict",
    )

    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: response.output_text.delta"
            yield 'data: {"delta":"今天"}'
            yield ""
            yield "event: response.completed"
            yield 'data: {"type":"response.completed","response":{"id":"resp_123","output":[]}}'
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)

    with pytest.raises(ConfigurationError, match="output must be a non-empty list"):
        asyncio.run(
            stream_support.execute_stream_probe_request(
                request,
                api_dialect="openai_responses",
                print_response=False,
            )
        )


def test_execute_stream_probe_request_rejects_conflicting_openai_terminal_text(
    monkeypatch,
) -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://proxy.example.com/v1/responses",
        headers={"Accept": "text/event-stream"},
        json_body={"model": "gpt-5.2-codex", "stream": True},
    )

    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: response.output_text.delta"
            yield 'data: {"delta":"今天有新闻"}'
            yield ""
            yield "event: response.completed"
            yield (
                'data: {"type":"response.completed","response":{"output":[{"type":"message",'
                '"content":[{"type":"output_text","text":"明天有雨"}]}]}}'
            )
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)

    with pytest.raises(ConfigurationError, match="流式终态文本与已累计的增量文本不一致"):
        asyncio.run(
            stream_support.execute_stream_probe_request(
                request,
                api_dialect="openai_responses",
                print_response=False,
            )
        )


def test_execute_stream_probe_request_keeps_slow_openai_stream_alive(monkeypatch) -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://proxy.example.com/v1/responses",
        headers={"Accept": "text/event-stream"},
        json_body={"model": "gpt-5.2-codex", "stream": True},
    )

    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: response.created"
            yield 'data: {"type":"response.created"}'
            yield ""
            await asyncio.sleep(stream_support.STREAM_STOP_CHECK_INTERVAL_SECONDS + 0.05)
            yield "event: response.output_text.delta"
            yield 'data: {"delta":"今天"}'
            yield ""
            yield "event: response.completed"
            yield 'data: {"type":"response.completed"}'
            yield ""
            yield "data: [DONE]"
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)

    normalized = asyncio.run(
        stream_support.execute_stream_probe_request(
            request,
            api_dialect="openai_responses",
            print_response=False,
        )
    )

    assert normalized.content == "今天"


def test_flush_stream_event_extracts_openai_chat_truncation_reason() -> None:
    buffer = stream_support.StreamEventBuffer(
        event_name=None,
        data_lines=[
            json_line('{"choices":[{"delta":{"content":"今天"},"finish_reason":"length"}]}'),
        ],
    )

    events = stream_support._flush_stream_event(
        buffer,
        api_dialect="openai_chat_completions",
    )

    assert len(events) == 1
    assert events[0].delta == "今天"
    assert events[0].stop_reason == "length"
    assert stream_support.extract_stream_truncation_reason(events[0].stop_reason) == "length"


def test_flush_stream_event_extracts_gemini_max_tokens_reason() -> None:
    buffer = stream_support.StreamEventBuffer(
        event_name=None,
        data_lines=[
            json_line(
                '{"candidates":[{"finishReason":"MAX_TOKENS","content":{"parts":[{"text":"今天"}]}}]}'
            ),
        ],
    )

    events = stream_support._flush_stream_event(
        buffer,
        api_dialect="gemini_generate_content",
    )

    assert len(events) == 1
    assert events[0].delta == "今天"
    assert events[0].stop_reason == "MAX_TOKENS"
    assert stream_support.extract_stream_truncation_reason(events[0].stop_reason) == "MAX_TOKENS"


def test_iterate_stream_request_stops_when_callback_requests_interrupt(monkeypatch) -> None:
    request = PreparedLLMHttpRequest(
        method="POST",
        url="https://proxy.example.com/v1/responses",
        headers={"Accept": "text/event-stream"},
        json_body={"model": "gpt-5.2-codex", "stream": True},
    )

    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aread(self):
            return b""

        async def aiter_lines(self):
            yield "event: response.output_text.delta"
            yield 'data: {"delta":"今天"}'
            yield ""
            await asyncio.sleep(1)
            yield "event: response.output_text.delta"
            yield 'data: {"delta":"还有后续"}'
            yield ""

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return FakeResponse()

    stop_checks = {"count": 0}

    async def should_stop() -> bool:
        stop_checks["count"] += 1
        return stop_checks["count"] > 4

    monkeypatch.setattr(stream_support.httpx, "AsyncClient", FakeClient)

    async def collect() -> list[str]:
        parts: list[str] = []
        with pytest.raises(stream_support.StreamInterruptedError):
            async for event in stream_support.iterate_stream_request(
                request,
                api_dialect="openai_responses",
                should_stop=should_stop,
            ):
                parts.append(event.delta)
        return parts

    assert asyncio.run(collect()) == ["今天"]


def json_line(value: str) -> str:
    return value
