from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

import httpx

from app.shared.runtime.errors import BusinessRuleError

VERIFY_TIMEOUT_SECONDS = 5
ANTHROPIC_VERSION = "2023-06-01"
OPENAI_COMPATIBLE_PROVIDERS = frozenset({"openai", "deepseek"})
DEFAULT_VERIFY_URLS = {
    "openai": "https://api.openai.com/v1/models",
    "deepseek": "https://api.deepseek.com/v1/models",
    "anthropic": "https://api.anthropic.com/v1/models",
}


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
    ) -> CredentialVerificationResult: ...


class AsyncHttpCredentialVerifier:
    async def verify(
        self,
        *,
        provider: str,
        api_key: str,
        base_url: str | None,
    ) -> CredentialVerificationResult:
        normalized_provider = provider.lower()
        if normalized_provider not in DEFAULT_VERIFY_URLS:
            raise BusinessRuleError(f"Unsupported credential provider: {provider}")
        url = _resolve_verify_url(normalized_provider, base_url)
        headers = _build_headers(normalized_provider, api_key)
        try:
            async with httpx.AsyncClient(timeout=VERIFY_TIMEOUT_SECONDS) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            self._raise_http_error(provider, exc.response.status_code)
        except httpx.RequestError as exc:
            raise BusinessRuleError(f"无法连接到 {provider}") from exc
        return CredentialVerificationResult(
            verified_at=datetime.now(timezone.utc),
            message="Credential verified",
        )

    def _raise_http_error(self, provider: str, status_code: int) -> None:
        if status_code in {401, 403}:
            raise BusinessRuleError("API Key 无效")
        if status_code == 402:
            raise BusinessRuleError("该 Key 余额不足")
        raise BusinessRuleError(f"无法验证 {provider} 凭证: HTTP {status_code}")


def _resolve_verify_url(provider: str, base_url: str | None) -> str:
    if not base_url:
        return DEFAULT_VERIFY_URLS[provider]
    normalized = base_url.rstrip("/")
    if normalized.endswith("/models"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/models"
    return f"{normalized}/v1/models"


def _build_headers(provider: str, api_key: str) -> dict[str, str]:
    if provider in OPENAI_COMPATIBLE_PROVIDERS:
        return {"Authorization": f"Bearer {api_key}"}
    return {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
    }
