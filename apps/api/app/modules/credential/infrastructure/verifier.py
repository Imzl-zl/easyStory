from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Literal, Protocol

import httpx

from app.shared.runtime.errors import BusinessRuleError, ConfigurationError
from app.shared.runtime.llm.interop.provider_interop_stream_support import build_stream_probe_request
from app.shared.runtime.llm.interop.provider_tool_conformance_support import (
    ConformanceProbeKind,
    build_conformance_probe_request,
    build_tool_continuation_probe_result_echo,
    build_tool_continuation_probe_followup_request,
    normalize_conformance_probe_kind,
    normalize_text_probe_error_message,
    use_buffered_text_probe_by_default,
    validate_tool_call_probe_response,
    validate_tool_continuation_probe_response,
    validate_tool_definition_probe_response,
    VERIFY_EMPTY_CONTENT_MESSAGE,
)
from app.shared.runtime.llm.llm_backend import AsyncLLMGenerateBackend, resolve_backend_selection
from app.shared.runtime.llm.litellm_backend import LiteLLMBackend
from app.shared.runtime.llm.llm_protocol_requests import prepare_generation_request
from app.shared.runtime.llm.llm_protocol_types import (
    LLMConnection,
    LLMGenerateRequest,
    NormalizedLLMResponse,
    PreparedLLMHttpRequest,
    resolve_model_name,
)
from app.shared.runtime.llm.native_http_backend import NativeHttpLLMBackend
from app.shared.runtime.llm.llm_response_validation import raise_if_empty_tool_response

# Tool probes can trigger reasoning/tool-planning paths, so a very short
# timeout creates false negatives for otherwise healthy providers.
STREAM_HTTP_ERROR_PATTERN = re.compile(
    r"^LLM streaming request failed: HTTP (?P<status>\d{3})(?: - (?P<detail>.*))?$"
)
REQUEST_HTTP_ERROR_PATTERN = re.compile(
    r"^LLM request failed: HTTP (?P<status>\d{3})(?: - (?P<detail>.*))?$"
)
CredentialVerifyTransportMode = Literal["stream", "buffered"]


@dataclass(frozen=True)
class CredentialVerificationResult:
    verified_at: datetime
    message: str
    probe_kind: ConformanceProbeKind
    transport_mode: CredentialVerifyTransportMode | None = None


class AsyncCredentialVerifier(Protocol):
    async def verify(
        self,
        *,
        provider: str,
        api_key: str,
        base_url: str | None,
        api_dialect: str,
        default_model: str | None,
        interop_profile: str | None,
        auth_strategy: str | None,
        api_key_header_name: str | None,
        extra_headers: dict[str, str] | None,
        user_agent_override: str | None,
        client_name: str | None,
        client_version: str | None,
        runtime_kind: str | None,
        probe_kind: ConformanceProbeKind | None = None,
        transport_mode: CredentialVerifyTransportMode | None = None,
    ) -> CredentialVerificationResult: ...


class AsyncCredentialStreamRequestSender(Protocol):
    async def __call__(
        self,
        request: PreparedLLMHttpRequest,
        *,
        api_dialect: str,
    ) -> NormalizedLLMResponse: ...


class AsyncHttpCredentialVerifier:
    def __init__(
        self,
        *,
        stream_request_sender: AsyncCredentialStreamRequestSender | None = None,
        backend: AsyncLLMGenerateBackend | None = None,
        litellm_backend: AsyncLLMGenerateBackend | None = None,
        native_backend: AsyncLLMGenerateBackend | None = None,
    ) -> None:
        self.stream_request_sender = stream_request_sender
        self.default_backend = backend
        self.litellm_backend = litellm_backend or backend or LiteLLMBackend()
        self.native_backend = native_backend or NativeHttpLLMBackend()

    async def verify(
        self,
        *,
        provider: str,
        api_key: str,
        base_url: str | None,
        api_dialect: str,
        default_model: str | None,
        interop_profile: str | None = None,
        auth_strategy: str | None = None,
        api_key_header_name: str | None = None,
        extra_headers: dict[str, str] | None = None,
        user_agent_override: str | None = None,
        client_name: str | None = None,
        client_version: str | None = None,
        runtime_kind: str | None = None,
        probe_kind: ConformanceProbeKind | None = None,
        transport_mode: CredentialVerifyTransportMode | None = None,
    ) -> CredentialVerificationResult:
        normalized_probe_kind = normalize_conformance_probe_kind(probe_kind)
        normalized_transport_mode = _normalize_probe_transport_mode(
            probe_kind=normalized_probe_kind,
            transport_mode=transport_mode,
        )
        connection = LLMConnection(
            provider=provider,
            api_dialect=api_dialect,
            api_key=api_key,
            base_url=base_url,
            default_model=default_model,
            interop_profile=interop_profile,
            auth_strategy=auth_strategy,
            api_key_header_name=api_key_header_name,
            extra_headers=extra_headers,
            user_agent_override=user_agent_override,
            client_name=client_name,
            client_version=client_version,
            runtime_kind=runtime_kind,
        )
        try:
            model_name = resolve_model_name(
                requested_model_name=None,
                default_model=default_model,
                provider_label="credential verification",
            )
            await self._verify_conformance_probe(
                provider,
                connection=connection,
                model_name=model_name,
                api_dialect=api_dialect,
                probe_kind=normalized_probe_kind,
                transport_mode=normalized_transport_mode,
            )
        except ConfigurationError as exc:
            _raise_stream_http_error(
                provider,
                exc,
                probe_kind=normalized_probe_kind,
                transport_mode=normalized_transport_mode,
            )
            if normalized_probe_kind == "text_probe":
                raise BusinessRuleError(str(exc)) from exc
            raise BusinessRuleError(
                _format_probe_failure_message(
                    provider,
                    probe_kind=normalized_probe_kind,
                    transport_mode=normalized_transport_mode,
                    detail=str(exc),
                )
            ) from exc
        except httpx.RequestError as exc:
            raise BusinessRuleError(f"无法连接到 {provider}") from exc
        return CredentialVerificationResult(
            verified_at=datetime.now(timezone.utc),
            message=_resolve_probe_success_message(
                normalized_probe_kind,
                transport_mode=normalized_transport_mode,
            ),
            probe_kind=normalized_probe_kind,
            transport_mode=normalized_transport_mode,
        )

    async def _verify_conformance_probe(
        self,
        provider: str,
        *,
        connection: LLMConnection,
        model_name: str,
        api_dialect: str,
        probe_kind: ConformanceProbeKind,
        transport_mode: CredentialVerifyTransportMode | None,
    ) -> None:
        initial_response = await self._execute_probe_request(
            build_conformance_probe_request(
                connection,
                model_name=model_name,
                probe_kind=probe_kind,
            ),
            api_dialect=api_dialect,
            probe_kind=probe_kind,
            transport_mode=transport_mode,
        )
        if probe_kind == "text_probe":
            self._validate_text_probe_response(provider, initial_response)
            return
        if probe_kind == "tool_definition_probe":
            validate_tool_definition_probe_response(initial_response)
            return
        if probe_kind == "tool_call_probe":
            validate_tool_call_probe_response(initial_response)
            return
        result_echo = build_tool_continuation_probe_result_echo()
        validate_tool_call_probe_response(initial_response)
        followup_response = await self._execute_probe_request(
            build_tool_continuation_probe_followup_request(
                connection,
                model_name=model_name,
                initial_response=initial_response,
                result_echo=result_echo,
            ),
            api_dialect=api_dialect,
            probe_kind=probe_kind,
            transport_mode=transport_mode,
        )
        validate_tool_continuation_probe_response(
            followup_response,
            expected_echo=result_echo,
        )

    async def _execute_probe_request(
        self,
        request: LLMGenerateRequest,
        *,
        api_dialect: str,
        probe_kind: ConformanceProbeKind,
        transport_mode: CredentialVerifyTransportMode | None,
    ) -> NormalizedLLMResponse:
        if probe_kind == "text_probe":
            return await self._execute_text_probe_request(
                request,
                api_dialect=api_dialect,
                transport_mode=transport_mode,
            )
        if transport_mode == "buffered":
            response = await self._resolve_backend(request).generate(request)
        else:
            response = await self._execute_stream_probe_request(request)
        raise_if_empty_tool_response(
            has_tools=bool(request.tools),
            content=response.content,
            tool_calls=response.tool_calls,
        )
        return response

    async def _execute_text_probe_request(
        self,
        request: LLMGenerateRequest,
        *,
        api_dialect: str,
        transport_mode: CredentialVerifyTransportMode | None,
    ) -> NormalizedLLMResponse:
        if transport_mode == "buffered":
            return await self._resolve_backend(request).generate(request)
        if transport_mode == "stream":
            return await self._execute_text_probe_stream_request(request)
        if transport_mode is None and use_buffered_text_probe_by_default(api_dialect):
            return await self._resolve_backend(request).generate(request)
        return await self._execute_text_probe_stream_request(request)

    async def _execute_text_probe_stream_request(
        self,
        request: LLMGenerateRequest,
    ) -> NormalizedLLMResponse:
        return await self._execute_stream_probe_request(request)

    async def _execute_stream_probe_request(
        self,
        request: LLMGenerateRequest,
    ) -> NormalizedLLMResponse:
        if self.stream_request_sender is not None:
            return await _execute_stream_request_with_sender(
                self.stream_request_sender,
                request,
            )
        terminal_response: NormalizedLLMResponse | None = None
        async for event in self._resolve_backend(request).generate_stream(request):
            if event.terminal_response is not None:
                terminal_response = event.terminal_response
        if terminal_response is None:
            raise ConfigurationError("Streaming backend completed without terminal response")
        return terminal_response

    def _resolve_backend(self, request: LLMGenerateRequest) -> AsyncLLMGenerateBackend:
        if self.default_backend is not None:
            return self.default_backend
        selection = resolve_backend_selection(request)
        if selection.backend_key == "native_http":
            return self.native_backend
        return self.litellm_backend

    def _validate_text_probe_response(
        self,
        provider: str,
        response: NormalizedLLMResponse,
    ) -> None:
        actual_reply = response.content.strip()
        if not actual_reply:
            raise BusinessRuleError(
                f"无法验证 {provider} 凭证: {VERIFY_EMPTY_CONTENT_MESSAGE}"
            )
        upstream_error = normalize_text_probe_error_message(actual_reply)
        if upstream_error is not None:
            raise BusinessRuleError(f"无法验证 {provider} 凭证: {upstream_error}")


async def _execute_stream_request_with_sender(
    sender: AsyncCredentialStreamRequestSender,
    request: LLMGenerateRequest,
) -> NormalizedLLMResponse:
    prepared_request = build_stream_probe_request(
        prepare_generation_request(request),
        api_dialect=request.connection.api_dialect,
    )
    return await sender(
        prepared_request,
        api_dialect=request.connection.api_dialect,
    )


def _raise_stream_http_error(
    provider: str,
    error: ConfigurationError,
    *,
    probe_kind: ConformanceProbeKind,
    transport_mode: CredentialVerifyTransportMode | None,
) -> None:
    detail = str(error).strip()
    match = STREAM_HTTP_ERROR_PATTERN.match(detail) or REQUEST_HTTP_ERROR_PATTERN.match(detail)
    if match is None:
        return
    status_code = int(match.group("status"))
    error_detail = match.group("detail") or "unknown error"
    if status_code in {401, 403}:
        raise BusinessRuleError("API Key 无效") from error
    if status_code == 402:
        raise BusinessRuleError("该 Key 余额不足") from error
    if status_code == 404:
        raise BusinessRuleError(f"{provider} 接口地址无效或接口类型不匹配") from error
    raise BusinessRuleError(
        _format_probe_failure_message(
            provider,
            probe_kind=probe_kind,
            transport_mode=transport_mode,
            detail=f"HTTP {status_code} - {error_detail}",
        )
    ) from error


def _normalize_probe_transport_mode(
    *,
    probe_kind: ConformanceProbeKind,
    transport_mode: CredentialVerifyTransportMode | None,
) -> CredentialVerifyTransportMode | None:
    if probe_kind == "text_probe":
        if transport_mode is None:
            return None
        if transport_mode not in {"stream", "buffered"}:
            raise BusinessRuleError("transport_mode 仅支持 stream 或 buffered。")
        return transport_mode
    if transport_mode is None:
        raise BusinessRuleError("工具验证必须显式指定 transport_mode。")
    if transport_mode not in {"stream", "buffered"}:
        raise BusinessRuleError("transport_mode 仅支持 stream 或 buffered。")
    return transport_mode


def _format_probe_failure_message(
    provider: str,
    *,
    probe_kind: ConformanceProbeKind,
    transport_mode: CredentialVerifyTransportMode | None,
    detail: str,
) -> str:
    label = _resolve_probe_failure_label(
        probe_kind,
        transport_mode=transport_mode,
    )
    if label is None:
        return f"无法验证 {provider} 凭证: {detail}"
    return f"无法验证 {provider} 凭证: {label}：{detail}"


def _resolve_probe_failure_label(
    probe_kind: ConformanceProbeKind,
    *,
    transport_mode: CredentialVerifyTransportMode | None,
) -> str | None:
    if probe_kind == "text_probe":
        if transport_mode == "buffered":
            return "非流连接验证失败"
        if transport_mode == "stream":
            return "流式连接验证失败"
        return None
    if probe_kind == "tool_definition_probe":
        return f"{_resolve_transport_mode_label(transport_mode)}工具定义验证失败"
    return f"{_resolve_transport_mode_label(transport_mode)}工具调用验证失败"


def _resolve_probe_success_message(
    probe_kind: ConformanceProbeKind,
    *,
    transport_mode: CredentialVerifyTransportMode | None,
) -> str:
    if probe_kind == "text_probe":
        if transport_mode == "buffered":
            return "非流连接验证成功"
        if transport_mode == "stream":
            return "流式连接验证成功"
        return "验证成功"
    if probe_kind == "tool_definition_probe":
        return f"{_resolve_transport_mode_label(transport_mode)}工具定义验证成功"
    return f"{_resolve_transport_mode_label(transport_mode)}工具调用验证成功"


def _resolve_transport_mode_label(
    transport_mode: CredentialVerifyTransportMode | None,
) -> str:
    if transport_mode == "buffered":
        return "非流"
    return "流式"
