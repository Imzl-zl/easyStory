from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Protocol

import httpx

from app.shared.runtime.errors import BusinessRuleError, ConfigurationError
from app.shared.runtime.llm.interop.provider_tool_conformance_support import (
    ConformanceProbeKind,
    build_tool_continuation_probe_result_echo,
    build_conformance_probe_request,
    build_tool_continuation_probe_followup_request,
    normalize_conformance_probe_kind,
    validate_tool_call_probe_response,
    validate_tool_continuation_probe_response,
    validate_tool_definition_probe_response,
)
from app.shared.runtime.llm.llm_protocol import (
    LLMConnection,
    NormalizedLLMResponse,
    PreparedLLMHttpRequest,
    parse_generation_response,
    resolve_model_name,
    send_json_http_request,
)
from app.shared.runtime.llm.llm_response_validation import raise_if_truncated_response
from app.shared.runtime.llm.interop.provider_interop_stream_support import (
    build_stream_completion,
    build_stream_probe_request,
    execute_stream_probe_request,
    iterate_stream_request,
    synthesize_stream_terminal_response,
)

VERIFY_TIMEOUT_SECONDS = 5
VERIFY_TEXT_PROBE_TIMEOUT_SECONDS = 30
VERIFY_EMPTY_CONTENT_MESSAGE = "测试消息没有返回可用内容"
TEXT_PROBE_JSON_DIALECTS = frozenset({"anthropic_messages", "gemini_generate_content"})
RETIRED_MODEL_MARKERS = (
    "is no longer available",
    "please switch to",
)
MODEL_CONFIGURATION_ERROR_MARKERS = (
    "not supported for this model",
    "unsupported model",
    "invalid model",
    "unknown model",
    "does not exist",
    "model_not_found",
)
STREAM_HTTP_ERROR_PATTERN = re.compile(
    r"^LLM streaming request failed: HTTP (?P<status>\d{3})(?: - (?P<detail>.*))?$"
)
REQUEST_HTTP_ERROR_PATTERN = re.compile(
    r"^LLM request failed: HTTP (?P<status>\d{3})(?: - (?P<detail>.*))?$"
)


@dataclass(frozen=True)
class CredentialVerificationResult:
    verified_at: datetime
    message: str
    probe_kind: ConformanceProbeKind


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
    ) -> None:
        self.stream_request_sender = stream_request_sender

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
    ) -> CredentialVerificationResult:
        normalized_probe_kind = normalize_conformance_probe_kind(probe_kind)
        connection = LLMConnection(
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
            )
        except ConfigurationError as exc:
            _raise_stream_http_error(provider, exc, probe_kind=normalized_probe_kind)
            if normalized_probe_kind == "text_probe":
                raise BusinessRuleError(str(exc)) from exc
            raise BusinessRuleError(
                _format_probe_failure_message(
                    provider,
                    probe_kind=normalized_probe_kind,
                    detail=str(exc),
                )
            ) from exc
        except httpx.RequestError as exc:
            raise BusinessRuleError(f"无法连接到 {provider}") from exc
        return CredentialVerificationResult(
            verified_at=datetime.now(timezone.utc),
            message=_resolve_probe_success_message(normalized_probe_kind),
            probe_kind=normalized_probe_kind,
        )

    async def _verify_conformance_probe(
        self,
        provider: str,
        *,
        connection: LLMConnection,
        model_name: str,
        api_dialect: str,
        probe_kind: ConformanceProbeKind,
    ) -> None:
        initial_response = await self._execute_probe_request(
            build_conformance_probe_request(
                connection,
                model_name=model_name,
                probe_kind=probe_kind,
            ),
            api_dialect=api_dialect,
            probe_kind=probe_kind,
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
        )
        validate_tool_continuation_probe_response(
            followup_response,
            expected_echo=result_echo,
        )

    async def _execute_probe_request(
        self,
        request: PreparedLLMHttpRequest,
        *,
        api_dialect: str,
        probe_kind: ConformanceProbeKind,
    ) -> NormalizedLLMResponse:
        if probe_kind == "text_probe" and self.stream_request_sender is None:
            if api_dialect in TEXT_PROBE_JSON_DIALECTS:
                return await _default_text_probe_json_request_sender(
                    request,
                    api_dialect=api_dialect,
                )
            return await _default_text_probe_request_sender(
                build_stream_probe_request(request, api_dialect=api_dialect),
                api_dialect=api_dialect,
            )
        streamed_request = build_stream_probe_request(request, api_dialect=api_dialect)
        sender = self.stream_request_sender or _default_stream_request_sender
        return await sender(streamed_request, api_dialect=api_dialect)

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
        upstream_error = _normalize_probe_error_message(actual_reply)
        if upstream_error is not None:
            raise BusinessRuleError(f"无法验证 {provider} 凭证: {upstream_error}")


def _raise_stream_http_error(
    provider: str,
    error: ConfigurationError,
    *,
    probe_kind: ConformanceProbeKind,
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
            detail=f"HTTP {status_code} - {error_detail}",
        )
    ) from error


async def _default_stream_request_sender(
    request: PreparedLLMHttpRequest,
    *,
    api_dialect: str,
) -> NormalizedLLMResponse:
    return await execute_stream_probe_request(
        request,
        api_dialect=api_dialect,
        print_response=False,
        timeout_seconds=VERIFY_TIMEOUT_SECONDS,
    )


async def _default_text_probe_request_sender(
    request: PreparedLLMHttpRequest,
    *,
    api_dialect: str,
) -> NormalizedLLMResponse:
    text_parts: list[str] = []
    raw_event_tuples: list[tuple[str | None, dict[str, object]]] = []
    terminal_response: NormalizedLLMResponse | None = None
    async for event in iterate_stream_request(
        request,
        api_dialect=api_dialect,
        print_status=True,
        timeout_seconds=VERIFY_TEXT_PROBE_TIMEOUT_SECONDS,
    ):
        raw_event_tuples.append((event.event_name, event.payload))
        if event.delta:
            text_parts.append(event.delta)
            partial_content = "".join(text_parts).strip()
            if partial_content:
                return NormalizedLLMResponse(
                    content=partial_content,
                    finish_reason=None,
                    input_tokens=None,
                    output_tokens=None,
                    total_tokens=None,
                )
        if event.terminal_response is None:
            continue
        terminal_response = event.terminal_response
        normalized = build_stream_completion(
            api_dialect=api_dialect,
            text_parts=text_parts,
            terminal_response=terminal_response,
        )
        if normalized is not None and normalized.content.strip():
            return normalized
    synthesized_terminal = synthesize_stream_terminal_response(
        api_dialect,
        raw_events=raw_event_tuples,
        tool_name_aliases=request.tool_name_aliases,
    )
    if synthesized_terminal is not None:
        terminal_response = synthesized_terminal
    normalized = build_stream_completion(
        api_dialect=api_dialect,
        text_parts=text_parts,
        terminal_response=terminal_response,
    )
    if normalized is None or not normalized.content.strip():
        raise ConfigurationError("Streaming probe returned no text content")
    return normalized


async def _default_text_probe_json_request_sender(
    request: PreparedLLMHttpRequest,
    *,
    api_dialect: str,
) -> NormalizedLLMResponse:
    response = await send_json_http_request(
        request,
        timeout_seconds=VERIFY_TEXT_PROBE_TIMEOUT_SECONDS,
    )
    if response.status_code >= 400:
        raise ConfigurationError(_build_request_http_error_message(response))
    raise_if_truncated_response(
        api_dialect=api_dialect,
        payload=response.json_body or {},
    )
    return parse_generation_response(
        api_dialect,
        response.json_body or {},
        tool_name_aliases=request.tool_name_aliases,
    )


def _normalize_probe_error_message(reply: str) -> str | None:
    normalized_reply = reply.strip()
    lowered_reply = normalized_reply.lower()
    if any(marker in lowered_reply for marker in RETIRED_MODEL_MARKERS):
        return f"当前默认模型已不可用，请换成可用模型后再试。上游提示：{normalized_reply}"
    if any(marker in lowered_reply for marker in MODEL_CONFIGURATION_ERROR_MARKERS):
        return f"默认模型或接口类型不匹配。上游提示：{normalized_reply}"
    return None


def _build_request_http_error_message(response) -> str:
    if response.json_body is not None:
        error = response.json_body.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return f"LLM request failed: HTTP {response.status_code} - {error['message']}"
        if isinstance(error, str):
            return f"LLM request failed: HTTP {response.status_code} - {error}"
    suffix = response.text.strip()
    if suffix:
        return f"LLM request failed: HTTP {response.status_code} - {suffix}"
    return f"LLM request failed: HTTP {response.status_code}"


def _format_probe_failure_message(
    provider: str,
    *,
    probe_kind: ConformanceProbeKind,
    detail: str,
) -> str:
    label = _resolve_probe_failure_label(probe_kind)
    if label is None:
        return f"无法验证 {provider} 凭证: {detail}"
    return f"无法验证 {provider} 凭证: {label}：{detail}"


def _resolve_probe_failure_label(
    probe_kind: ConformanceProbeKind,
) -> str | None:
    if probe_kind == "text_probe":
        return None
    if probe_kind == "tool_definition_probe":
        return "工具定义验证失败"
    return "工具调用验证失败"


def _resolve_probe_success_message(probe_kind: ConformanceProbeKind) -> str:
    if probe_kind == "text_probe":
        return "验证成功"
    if probe_kind == "tool_definition_probe":
        return "工具定义验证成功"
    return "工具调用验证成功"
