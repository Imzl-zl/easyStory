from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Protocol

import httpx

from app.shared.runtime.errors import BusinessRuleError, ConfigurationError
from app.shared.runtime.llm_protocol import (
    LLMConnection,
    NormalizedLLMResponse,
    PreparedLLMHttpRequest,
    build_verification_request,
)
from app.shared.runtime.provider_interop_stream_support import (
    build_stream_probe_request,
    execute_stream_probe_request,
)

VERIFY_TIMEOUT_SECONDS = 5
VERIFY_EMPTY_CONTENT_MESSAGE = "测试消息没有返回可用内容"
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


@dataclass(frozen=True)
class CredentialVerificationResult:
    verified_at: datetime
    message: str


class AsyncCredentialVerifier(Protocol):
    async def verify(
        self,
        *,
        provider: str,
        api_key: str,
        base_url: str | None,
        api_dialect: str,
        default_model: str | None,
        auth_strategy: str | None,
        api_key_header_name: str | None,
        extra_headers: dict[str, str] | None,
        user_agent_override: str | None,
        client_name: str | None,
        client_version: str | None,
        runtime_kind: str | None,
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
        self.stream_request_sender = stream_request_sender or _default_stream_request_sender

    async def verify(
        self,
        *,
        provider: str,
        api_key: str,
        base_url: str | None,
        api_dialect: str,
        default_model: str | None,
        auth_strategy: str | None = None,
        api_key_header_name: str | None = None,
        extra_headers: dict[str, str] | None = None,
        user_agent_override: str | None = None,
        client_name: str | None = None,
        client_version: str | None = None,
        runtime_kind: str | None = None,
    ) -> CredentialVerificationResult:
        try:
            request = build_stream_probe_request(
                build_verification_request(
                    LLMConnection(
                        api_dialect=api_dialect,
                        api_key=api_key,
                        base_url=base_url,
                        default_model=default_model,
                        auth_strategy=auth_strategy,
                        api_key_header_name=api_key_header_name,
                        extra_headers=extra_headers,
                        user_agent_override=user_agent_override,
                        client_name=client_name,
                        client_version=client_version,
                        runtime_kind=runtime_kind,
                    )
                ),
                api_dialect=api_dialect,
            )
            normalized = await self.stream_request_sender(
                request,
                api_dialect=api_dialect,
            )
        except ConfigurationError as exc:
            _raise_stream_http_error(provider, exc)
            raise BusinessRuleError(str(exc)) from exc
        except httpx.RequestError as exc:
            raise BusinessRuleError(f"无法连接到 {provider}") from exc
        self._validate_probe_response(provider, normalized)
        return CredentialVerificationResult(
            verified_at=datetime.now(timezone.utc),
            message="验证成功",
        )

    def _validate_probe_response(
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


def _raise_stream_http_error(provider: str, error: ConfigurationError) -> None:
    detail = str(error).strip()
    match = STREAM_HTTP_ERROR_PATTERN.match(detail)
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
        f"无法验证 {provider} 凭证: HTTP {status_code} - {error_detail}"
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


def _normalize_probe_error_message(reply: str) -> str | None:
    normalized_reply = reply.strip()
    lowered_reply = normalized_reply.lower()
    if any(marker in lowered_reply for marker in RETIRED_MODEL_MARKERS):
        return f"当前默认模型已不可用，请换成可用模型后再试。上游提示：{normalized_reply}"
    if any(marker in lowered_reply for marker in MODEL_CONFIGURATION_ERROR_MARKERS):
        return f"默认模型或接口类型不匹配。上游提示：{normalized_reply}"
    return None
