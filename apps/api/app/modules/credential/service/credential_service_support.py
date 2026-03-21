from __future__ import annotations

from collections.abc import Callable

from app.modules.credential.infrastructure import CredentialVerificationResult
from app.modules.credential.models import ModelCredential

from .dto import CredentialUpdateDTO, CredentialVerifyResultDTO, CredentialViewDTO

MASKED_KEY_MIN_LENGTH = 7
MASKED_VISIBLE_PREFIX = 3
MASKED_VISIBLE_SUFFIX = 4


def apply_update_payload(
    credential: ModelCredential,
    payload: CredentialUpdateDTO,
    *,
    encrypt_api_key: Callable[[str], str],
) -> dict[str, str]:
    changes: dict[str, str] = {}
    update_display_name(credential, payload, changes)
    update_base_url(credential, payload, changes)
    rotate_api_key(credential, payload, encrypt_api_key=encrypt_api_key, changes=changes)
    return changes


def update_display_name(
    credential: ModelCredential,
    payload: CredentialUpdateDTO,
    changes: dict[str, str],
) -> None:
    if payload.display_name is None:
        return
    display_name = payload.display_name.strip()
    if display_name == credential.display_name:
        return
    credential.display_name = display_name
    changes["display_name"] = "updated"


def update_base_url(
    credential: ModelCredential,
    payload: CredentialUpdateDTO,
    changes: dict[str, str],
) -> None:
    if payload.base_url is None:
        return
    base_url = normalize_base_url(payload.base_url)
    if base_url == credential.base_url:
        return
    credential.base_url = base_url
    credential.last_verified_at = None
    changes["base_url"] = "updated"


def rotate_api_key(
    credential: ModelCredential,
    payload: CredentialUpdateDTO,
    encrypt_api_key: Callable[[str], str],
    changes: dict[str, str],
) -> None:
    if payload.api_key is None:
        return
    credential.encrypted_key = encrypt_api_key(payload.api_key)
    credential.last_verified_at = None
    changes["api_key"] = "rotated"


def to_view(
    credential: ModelCredential,
    *,
    decrypt_api_key: Callable[[str], str],
) -> CredentialViewDTO:
    return CredentialViewDTO(
        id=credential.id,
        owner_type=credential.owner_type,
        owner_id=credential.owner_id,
        provider=credential.provider,
        display_name=credential.display_name,
        masked_key=mask_key(decrypt_api_key(credential.encrypted_key)),
        base_url=credential.base_url,
        is_active=credential.is_active,
        last_verified_at=credential.last_verified_at,
    )


def to_verify_result(
    credential: ModelCredential,
    result: CredentialVerificationResult,
) -> CredentialVerifyResultDTO:
    return CredentialVerifyResultDTO(
        credential_id=credential.id,
        last_verified_at=result.verified_at,
        message=result.message,
    )


def normalize_provider(provider: str) -> str:
    return provider.strip().lower()


def normalize_base_url(base_url: str | None) -> str | None:
    if base_url is None:
        return None
    normalized = base_url.strip()
    return normalized or None


def mask_key(api_key: str) -> str:
    if len(api_key) < MASKED_KEY_MIN_LENGTH:
        return "***"
    return f"{api_key[:MASKED_VISIBLE_PREFIX]}...{api_key[-MASKED_VISIBLE_SUFFIX:]}"
