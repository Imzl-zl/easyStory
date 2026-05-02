from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import urlsplit
from typing import Protocol

from .llm_protocol_types import LLMGenerateRequest, NormalizedLLMResponse, resolve_auth_strategy

StreamStopChecker = Callable[[], Awaitable[bool]]

OPENAI_FULL_ENDPOINT_SUFFIXES = (
    "/v1/chat/completions",
    "/v1/responses",
)
ANTHROPIC_FULL_ENDPOINT_SUFFIXES = (
    "/v1/messages",
    "/v1/complete",
)
GEMINI_FULL_ENDPOINT_FRAGMENTS = (":generateContent", ":streamGenerateContent")


@dataclass(frozen=True)
class LLMBackendStreamEvent:
    delta: str = ""
    stop_reason: str | None = None
    terminal_response: NormalizedLLMResponse | None = None


class AsyncLLMGenerateBackend(Protocol):
    async def generate(self, request: LLMGenerateRequest) -> NormalizedLLMResponse: ...

    async def generate_stream(
        self,
        request: LLMGenerateRequest,
        *,
        should_stop: StreamStopChecker | None = None,
    ) -> AsyncIterator[LLMBackendStreamEvent]: ...


@dataclass(frozen=True)
class ResolvedLLMBackendSelection:
    backend_key: str
    reason: str


def resolve_backend_selection(request: LLMGenerateRequest) -> ResolvedLLMBackendSelection:
    auth_strategy = resolve_auth_strategy(
        request.connection.api_dialect,
        request.connection.auth_strategy,
    )
    if auth_strategy == "custom_header":
        return ResolvedLLMBackendSelection(
            backend_key="native_http",
            reason="custom_header 鉴权需要显式控制 API key header 写入方式",
        )
    if _uses_full_endpoint_base_url(request):
        return ResolvedLLMBackendSelection(
            backend_key="native_http",
            reason="已保存的完整 endpoint base_url 需要保留现有直连语义，避免 LiteLLM 再拼接路径",
        )
    if _uses_custom_gemini_base_url(request):
        return ResolvedLLMBackendSelection(
            backend_key="native_http",
            reason="Gemini 自定义网关需要保留 generateContent 原生路径语义",
        )
    if _uses_custom_openai_base_url(request):
        return ResolvedLLMBackendSelection(
            backend_key="native_http",
            reason="OpenAI 兼容自定义网关需要保留原生模型名与 Chat/Responses 请求语义",
        )
    if request.connection.api_dialect == "openai_responses" and request.stop:
        return ResolvedLLMBackendSelection(
            backend_key="native_http",
            reason="Responses + stop 目前继续保留现有原生 HTTP 语义",
        )
    if request.thinking_level is not None or _requires_native_thinking_budget(request):
        return ResolvedLLMBackendSelection(
            backend_key="native_http",
            reason="Gemini 原生 thinking 参数需要保留现有请求语义",
        )
    return ResolvedLLMBackendSelection(
        backend_key="litellm",
        reason="默认 southbound transport 走 LiteLLM 统一 provider 适配",
    )


def _requires_native_thinking_budget(request: LLMGenerateRequest) -> bool:
    if request.thinking_budget is None:
        return False
    if request.connection.api_dialect != "gemini_generate_content":
        return True
    return request.thinking_budget != 0


def _uses_custom_gemini_base_url(request: LLMGenerateRequest) -> bool:
    if request.connection.api_dialect != "gemini_generate_content":
        return False
    base_url = request.connection.base_url
    if base_url is None:
        return False
    hostname = (urlsplit(base_url).hostname or "").lower()
    return hostname != "generativelanguage.googleapis.com"


def _uses_custom_openai_base_url(request: LLMGenerateRequest) -> bool:
    if request.connection.api_dialect not in {"openai_chat_completions", "openai_responses"}:
        return False
    base_url = request.connection.base_url
    if base_url is None:
        return False
    hostname = (urlsplit(base_url).hostname or "").lower()
    return hostname != "api.openai.com"


def _uses_full_endpoint_base_url(request: LLMGenerateRequest) -> bool:
    base_url = request.connection.base_url
    if base_url is None:
        return False
    path = urlsplit(base_url).path.rstrip("/")
    if not path:
        return False
    if request.connection.api_dialect in {"openai_chat_completions", "openai_responses"}:
        return path.endswith(OPENAI_FULL_ENDPOINT_SUFFIXES)
    if request.connection.api_dialect == "anthropic_messages":
        return path.endswith(ANTHROPIC_FULL_ENDPOINT_SUFFIXES)
    if request.connection.api_dialect == "gemini_generate_content":
        return any(fragment in path for fragment in GEMINI_FULL_ENDPOINT_FRAGMENTS)
    return False
