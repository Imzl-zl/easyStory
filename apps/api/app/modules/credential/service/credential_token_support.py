from __future__ import annotations

from app.modules.credential.models import ModelCredential
from app.shared.runtime.errors import ConfigurationError

from .dto import CredentialUpdateDTO

CONTEXT_WINDOW_TOKENS_MIN = 256
CONTEXT_WINDOW_TOKENS_MAX = 2_000_000
DEFAULT_MAX_OUTPUT_TOKENS_MIN = 128
DEFAULT_MAX_OUTPUT_TOKENS_MAX = 131_072


def normalize_context_window_tokens(value: int | None) -> int | None:
    return _normalize_optional_token_limit(
        value,
        field_name="context_window_tokens",
        min_value=CONTEXT_WINDOW_TOKENS_MIN,
        max_value=CONTEXT_WINDOW_TOKENS_MAX,
    )


def normalize_default_max_output_tokens(value: int | None) -> int | None:
    return _normalize_optional_token_limit(
        value,
        field_name="default_max_output_tokens",
        min_value=DEFAULT_MAX_OUTPUT_TOKENS_MIN,
        max_value=DEFAULT_MAX_OUTPUT_TOKENS_MAX,
    )


def update_context_window_tokens(
    credential: ModelCredential,
    payload: CredentialUpdateDTO,
    changes: dict[str, str],
) -> None:
    if "context_window_tokens" not in payload.model_fields_set:
        return
    context_window_tokens = normalize_context_window_tokens(payload.context_window_tokens)
    if context_window_tokens == credential.context_window_tokens:
        return
    credential.context_window_tokens = context_window_tokens
    changes["context_window_tokens"] = "updated"


def update_default_max_output_tokens(
    credential: ModelCredential,
    payload: CredentialUpdateDTO,
    changes: dict[str, str],
) -> None:
    if "default_max_output_tokens" not in payload.model_fields_set:
        return
    default_max_output_tokens = normalize_default_max_output_tokens(
        payload.default_max_output_tokens
    )
    if default_max_output_tokens == credential.default_max_output_tokens:
        return
    credential.default_max_output_tokens = default_max_output_tokens
    changes["default_max_output_tokens"] = "updated"


def _normalize_optional_token_limit(
    value: int | None,
    *,
    field_name: str,
    min_value: int,
    max_value: int,
) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{field_name} must be an integer")
    if value < min_value:
        raise ConfigurationError(f"{field_name} is below the minimum")
    if value > max_value:
        raise ConfigurationError(f"{field_name} exceeds the maximum")
    return value


__all__ = [
    "CONTEXT_WINDOW_TOKENS_MAX",
    "CONTEXT_WINDOW_TOKENS_MIN",
    "DEFAULT_MAX_OUTPUT_TOKENS_MAX",
    "DEFAULT_MAX_OUTPUT_TOKENS_MIN",
    "normalize_context_window_tokens",
    "normalize_default_max_output_tokens",
    "update_context_window_tokens",
    "update_default_max_output_tokens",
]
