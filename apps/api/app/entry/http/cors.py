from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

CORS_ALLOWED_ORIGINS_ENV = "EASYSTORY_CORS_ALLOWED_ORIGINS"
CORS_ALLOWED_ORIGIN_REGEX_ENV = "EASYSTORY_CORS_ALLOWED_ORIGIN_REGEX"
DEFAULT_LOCAL_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"


def register_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_resolve_allowed_origins(),
        allow_origin_regex=_resolve_allowed_origin_regex(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _resolve_allowed_origins() -> list[str]:
    raw_origins = os.getenv(CORS_ALLOWED_ORIGINS_ENV, "")
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


def _resolve_allowed_origin_regex() -> str:
    configured_regex = os.getenv(CORS_ALLOWED_ORIGIN_REGEX_ENV)
    if configured_regex and configured_regex.strip():
        return configured_regex.strip()
    return DEFAULT_LOCAL_ORIGIN_REGEX
