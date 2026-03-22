from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

import httpx

from app.shared.runtime.errors import BusinessRuleError, ConfigurationError
from app.shared.runtime.llm_protocol import (
    HttpJsonResponse,
    LLMConnection,
    PreparedLLMHttpRequest,
    build_verification_request,
    send_json_http_request,
)

VERIFY_TIMEOUT_SECONDS = 5


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
        default_model: str,
    ) -> CredentialVerificationResult: ...


class AsyncCredentialRequestSender(Protocol):
    async def __call__(self, request: PreparedLLMHttpRequest) -> HttpJsonResponse: ...


class AsyncHttpCredentialVerifier:
    def __init__(
        self,
        *,
        request_sender: AsyncCredentialRequestSender | None = None,
    ) -> None:
        self.request_sender = request_sender or _default_request_sender

    async def verify(
        self,
        *,
        provider: str,
        api_key: str,
        base_url: str | None,
        api_dialect: str,
        default_model: str,
    ) -> CredentialVerificationResult:
        try:
            request = build_verification_request(
                LLMConnection(
                    api_dialect=api_dialect,
                    api_key=api_key,
                    base_url=base_url,
                    default_model=default_model,
                )
            )
            response = await self.request_sender(request)
        except ConfigurationError as exc:
            raise BusinessRuleError(str(exc)) from exc
        except httpx.RequestError as exc:
            raise BusinessRuleError(f"无法连接到 {provider}") from exc
        if response.status_code >= 400:
            self._raise_http_error(provider, response)
        return CredentialVerificationResult(
            verified_at=datetime.now(timezone.utc),
            message="Credential verified",
        )

    def _raise_http_error(self, provider: str, response: HttpJsonResponse) -> None:
        if response.status_code in {401, 403}:
            raise BusinessRuleError("API Key 无效")
        if response.status_code == 402:
            raise BusinessRuleError("该 Key 余额不足")
        if response.status_code == 404:
            raise BusinessRuleError(f"{provider} 接口地址无效或接口类型不匹配")
        message = _extract_error_message(response)
        raise BusinessRuleError(f"无法验证 {provider} 凭证: HTTP {response.status_code} - {message}")


def _extract_error_message(response: HttpJsonResponse) -> str:
    if response.json_body is not None:
        error = response.json_body.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
        if isinstance(error, str):
            return error
        message = response.json_body.get("message")
        if isinstance(message, str):
            return message
    return response.text.strip() or "unknown error"


async def _default_request_sender(request: PreparedLLMHttpRequest) -> HttpJsonResponse:
    return await send_json_http_request(request, timeout_seconds=VERIFY_TIMEOUT_SECONDS)
