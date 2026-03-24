from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.shared.runtime.errors import ConfigurationError

API_ROOT = Path(__file__).resolve().parents[2]
API_ENV_FILE = API_ROOT / ".env"

DATABASE_URL_ENV = "EASYSTORY_DATABASE_URL"
JWT_SECRET_ENV = "EASYSTORY_JWT_SECRET"
JWT_EXPIRE_HOURS_ENV = "EASYSTORY_JWT_EXPIRE_HOURS"
CREDENTIAL_MASTER_KEY_ENV = "EASYSTORY_CREDENTIAL_MASTER_KEY"
CORS_ALLOWED_ORIGINS_ENV = "EASYSTORY_CORS_ALLOWED_ORIGINS"
CORS_ALLOWED_ORIGIN_REGEX_ENV = "EASYSTORY_CORS_ALLOWED_ORIGIN_REGEX"
ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV = "EASYSTORY_ALLOW_PRIVATE_MODEL_ENDPOINTS"
CONFIG_ADMIN_USERNAMES_ENV = "EASYSTORY_CONFIG_ADMIN_USERNAMES"

DEFAULT_JWT_EXPIRE_HOURS = 24
DEFAULT_LOCAL_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
DEFAULT_ALLOW_PRIVATE_MODEL_ENDPOINTS = False
ENV_SETUP_HINT = "请参考 apps/api/.env.example 创建 apps/api/.env 并填写必需项。"
TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes", "on"})
FALSY_ENV_VALUES = frozenset({"0", "false", "no", "off"})


def _parse_integer_env_value(value: Any, *, env_name: str) -> int:
    if isinstance(value, bool):
        raise ConfigurationError(f"Invalid integer for {env_name}: {value}")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError as exc:
            raise ConfigurationError(f"Invalid integer for {env_name}: {value}") from exc
    raise ConfigurationError(f"Invalid integer for {env_name}: {value}")


def _parse_boolean_env_value(value: Any, *, env_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in TRUTHY_ENV_VALUES:
            return True
        if normalized in FALSY_ENV_VALUES:
            return False
    raise ConfigurationError(f"Invalid boolean for {env_name}: {value}")


def _parse_string_list_env_value(value: Any, *, env_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
        return list(dict.fromkeys(items))
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return list(dict.fromkeys(items))
    raise ConfigurationError(f"{env_name} must be a comma-separated string or list")


class EasyStorySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=API_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        enable_decoding=False,
    )

    database_url: str | None = Field(default=None, validation_alias=DATABASE_URL_ENV)
    jwt_secret: str | None = Field(default=None, validation_alias=JWT_SECRET_ENV)
    jwt_expire_hours: int = Field(
        default=DEFAULT_JWT_EXPIRE_HOURS,
        validation_alias=JWT_EXPIRE_HOURS_ENV,
    )
    credential_master_key: str | None = Field(
        default=None,
        validation_alias=CREDENTIAL_MASTER_KEY_ENV,
    )
    cors_allowed_origins: list[str] = Field(
        default_factory=list,
        validation_alias=CORS_ALLOWED_ORIGINS_ENV,
    )
    cors_allowed_origin_regex: str = Field(
        default=DEFAULT_LOCAL_ORIGIN_REGEX,
        validation_alias=CORS_ALLOWED_ORIGIN_REGEX_ENV,
    )
    allow_private_model_endpoints: bool = Field(
        default=DEFAULT_ALLOW_PRIVATE_MODEL_ENDPOINTS,
        validation_alias=ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV,
    )
    config_admin_usernames: list[str] = Field(
        default_factory=list,
        validation_alias=CONFIG_ADMIN_USERNAMES_ENV,
    )

    @field_validator("jwt_expire_hours", mode="before")
    @classmethod
    def parse_jwt_expire_hours(cls, value: Any) -> int:
        return _parse_integer_env_value(value, env_name=JWT_EXPIRE_HOURS_ENV)

    @field_validator("jwt_expire_hours")
    @classmethod
    def validate_jwt_expire_hours(cls, value: int) -> int:
        if value <= 0:
            raise ConfigurationError(f"{JWT_EXPIRE_HOURS_ENV} must be > 0")
        return value

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_allowed_origins(cls, value: Any) -> list[str]:
        return _parse_string_list_env_value(value, env_name=CORS_ALLOWED_ORIGINS_ENV)

    @field_validator("allow_private_model_endpoints", mode="before")
    @classmethod
    def parse_allow_private_model_endpoints(cls, value: Any) -> bool:
        return _parse_boolean_env_value(value, env_name=ALLOW_PRIVATE_MODEL_ENDPOINTS_ENV)

    @field_validator("config_admin_usernames", mode="before")
    @classmethod
    def parse_config_admin_usernames(cls, value: Any) -> list[str]:
        return _parse_string_list_env_value(value, env_name=CONFIG_ADMIN_USERNAMES_ENV)

    def require_jwt_secret(self) -> str:
        if self.jwt_secret and self.jwt_secret.strip():
            return self.jwt_secret
        raise ConfigurationError(
            f"Missing required environment variable: {JWT_SECRET_ENV}. {ENV_SETUP_HINT}"
        )

    def require_credential_master_key(self) -> str:
        if self.credential_master_key and self.credential_master_key.strip():
            return self.credential_master_key
        raise ConfigurationError(
            "Missing required environment variable: "
            f"{CREDENTIAL_MASTER_KEY_ENV}. {ENV_SETUP_HINT}"
        )

    def is_config_admin(self, username: str) -> bool:
        return username in self.config_admin_usernames


@lru_cache(maxsize=1)
def get_settings() -> EasyStorySettings:
    return EasyStorySettings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()


def validate_startup_settings() -> None:
    get_settings().require_jwt_secret()
