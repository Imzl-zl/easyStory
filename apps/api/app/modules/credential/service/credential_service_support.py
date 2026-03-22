from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable

from app.modules.credential.infrastructure import CredentialVerificationResult
from app.modules.credential.models import ModelCredential
from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm_protocol import normalize_api_dialect

from .dto import CredentialUpdateDTO, CredentialVerifyResultDTO, CredentialViewDTO

MASKED_KEY_MIN_LENGTH = 7
MASKED_VISIBLE_PREFIX = 3
MASKED_VISIBLE_SUFFIX = 4


@dataclass(frozen=True)
class ResolvedCredentialModel:
    credential: ModelCredential
    model_name: str


def apply_update_payload(
    credential: ModelCredential,
    payload: CredentialUpdateDTO,
    *,
    encrypt_api_key: Callable[[str], str],
) -> dict[str, str]:
    changes: dict[str, str] = {}
    update_api_dialect(credential, payload, changes)
    update_display_name(credential, payload, changes)
    update_base_url(credential, payload, changes)
    update_default_model(credential, payload, changes)
    rotate_api_key(credential, payload, encrypt_api_key=encrypt_api_key, changes=changes)
    return changes


def build_credential(
    *,
    owner_type: str,
    owner_id,
    provider: str,
    api_dialect: str,
    display_name: str,
    encrypted_key: str,
    base_url: str | None,
    default_model: str,
) -> ModelCredential:
    return ModelCredential(
        owner_type=owner_type,
        owner_id=owner_id,
        provider=provider,
        api_dialect=normalize_api_dialect(api_dialect),
        display_name=display_name.strip(),
        encrypted_key=encrypted_key,
        base_url=normalize_base_url(base_url),
        default_model=normalize_default_model(default_model),
        is_active=True,
    )


def update_api_dialect(
    credential: ModelCredential,
    payload: CredentialUpdateDTO,
    changes: dict[str, str],
) -> None:
    if payload.api_dialect is None:
        return
    api_dialect = normalize_api_dialect(payload.api_dialect)
    if api_dialect == credential.api_dialect:
        return
    credential.api_dialect = api_dialect
    credential.last_verified_at = None
    changes["api_dialect"] = "updated"


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


def update_default_model(
    credential: ModelCredential,
    payload: CredentialUpdateDTO,
    changes: dict[str, str],
) -> None:
    if payload.default_model is None:
        return
    default_model = normalize_default_model(payload.default_model)
    if default_model == credential.default_model:
        return
    credential.default_model = default_model
    credential.last_verified_at = None
    changes["default_model"] = "updated"


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
        api_dialect=normalize_api_dialect(credential.api_dialect),
        display_name=credential.display_name,
        masked_key=mask_key(decrypt_api_key(credential.encrypted_key)),
        base_url=credential.base_url,
        default_model=credential.default_model,
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


def normalize_default_model(default_model: str | None) -> str | None:
    if default_model is None:
        return None
    normalized = default_model.strip()
    if not normalized:
        raise ConfigurationError("default_model must be a non-empty string")
    return normalized


def normalize_base_url(base_url: str | None) -> str | None:
    if base_url is None:
        return None
    normalized = base_url.strip()
    return normalized or None


def resolve_model_name(
    *,
    requested_model_name: str | None,
    default_model: str | None,
    provider: str,
) -> str:
    explicit = normalize_default_model(requested_model_name)
    if explicit is not None:
        return explicit
    fallback = normalize_default_model(default_model)
    if fallback is not None:
        return fallback
    raise ConfigurationError(f"Credential '{provider}' is missing executable model name")


def mask_key(api_key: str) -> str:
    if len(api_key) < MASKED_KEY_MIN_LENGTH:
        return "***"
    return f"{api_key[:MASKED_VISIBLE_PREFIX]}...{api_key[-MASKED_VISIBLE_SUFFIX:]}"
