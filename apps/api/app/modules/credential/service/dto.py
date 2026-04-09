from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.shared.runtime.llm.interop.provider_tool_conformance_support import (
    ConformanceProbeKind,
)
from app.shared.runtime.llm.llm_protocol import (
    LlmApiDialect,
    LlmAuthStrategy,
    LlmInteropProfile,
    LlmRuntimeKind,
)

CredentialOwnerType = Literal["system", "user", "project"]
CredentialExtraHeaders = dict[str, str]
CREDENTIAL_CONTEXT_WINDOW_TOKENS_MIN = 256
CREDENTIAL_CONTEXT_WINDOW_TOKENS_MAX = 2_000_000
CREDENTIAL_DEFAULT_MAX_OUTPUT_TOKENS_MIN = 128
CREDENTIAL_DEFAULT_MAX_OUTPUT_TOKENS_MAX = 131_072
CREDENTIAL_USER_AGENT_OVERRIDE_MAX_LENGTH = 300
CredentialVerifyProbeKind = ConformanceProbeKind
CredentialVerifyTransportMode = Literal["stream", "buffered"]


class CredentialCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_type: CredentialOwnerType
    project_id: uuid.UUID | None = None
    provider: str = Field(min_length=1, max_length=50)
    api_dialect: LlmApiDialect = "openai_chat_completions"
    display_name: str = Field(min_length=1, max_length=100)
    api_key: str = Field(min_length=1, max_length=500)
    base_url: str | None = Field(default=None, max_length=500)
    default_model: str = Field(min_length=1, max_length=100)
    interop_profile: LlmInteropProfile | None = None
    context_window_tokens: int | None = Field(
        default=None,
        ge=CREDENTIAL_CONTEXT_WINDOW_TOKENS_MIN,
        le=CREDENTIAL_CONTEXT_WINDOW_TOKENS_MAX,
    )
    default_max_output_tokens: int | None = Field(
        default=None,
        ge=CREDENTIAL_DEFAULT_MAX_OUTPUT_TOKENS_MIN,
        le=CREDENTIAL_DEFAULT_MAX_OUTPUT_TOKENS_MAX,
    )
    auth_strategy: LlmAuthStrategy | None = None
    api_key_header_name: str | None = Field(default=None, max_length=100)
    extra_headers: CredentialExtraHeaders | None = None
    user_agent_override: str | None = Field(
        default=None,
        max_length=CREDENTIAL_USER_AGENT_OVERRIDE_MAX_LENGTH,
    )
    client_name: str | None = Field(default=None, max_length=100)
    client_version: str | None = Field(default=None, max_length=50)
    runtime_kind: LlmRuntimeKind | None = None


class CredentialUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_dialect: LlmApiDialect | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    api_key: str | None = Field(default=None, min_length=1, max_length=500)
    base_url: str | None = Field(default=None, max_length=500)
    default_model: str | None = Field(default=None, min_length=1, max_length=100)
    interop_profile: LlmInteropProfile | None = None
    context_window_tokens: int | None = Field(
        default=None,
        ge=CREDENTIAL_CONTEXT_WINDOW_TOKENS_MIN,
        le=CREDENTIAL_CONTEXT_WINDOW_TOKENS_MAX,
    )
    default_max_output_tokens: int | None = Field(
        default=None,
        ge=CREDENTIAL_DEFAULT_MAX_OUTPUT_TOKENS_MIN,
        le=CREDENTIAL_DEFAULT_MAX_OUTPUT_TOKENS_MAX,
    )
    auth_strategy: LlmAuthStrategy | None = None
    api_key_header_name: str | None = Field(default=None, max_length=100)
    extra_headers: CredentialExtraHeaders | None = None
    user_agent_override: str | None = Field(
        default=None,
        max_length=CREDENTIAL_USER_AGENT_OVERRIDE_MAX_LENGTH,
    )
    client_name: str | None = Field(default=None, max_length=100)
    client_version: str | None = Field(default=None, max_length=50)
    runtime_kind: LlmRuntimeKind | None = None


class CredentialViewDTO(BaseModel):
    id: uuid.UUID
    owner_type: CredentialOwnerType
    owner_id: uuid.UUID | None
    provider: str
    api_dialect: LlmApiDialect
    display_name: str
    masked_key: str
    base_url: str | None
    default_model: str | None
    interop_profile: LlmInteropProfile | None
    stream_tool_verified_probe_kind: CredentialVerifyProbeKind | None
    stream_tool_last_verified_at: datetime | None
    buffered_tool_verified_probe_kind: CredentialVerifyProbeKind | None
    buffered_tool_last_verified_at: datetime | None
    context_window_tokens: int | None
    default_max_output_tokens: int | None
    auth_strategy: LlmAuthStrategy | None
    api_key_header_name: str | None
    extra_headers: CredentialExtraHeaders | None
    user_agent_override: str | None
    client_name: str | None
    client_version: str | None
    runtime_kind: LlmRuntimeKind | None
    is_active: bool
    last_verified_at: datetime | None


class CredentialVerifyResultDTO(BaseModel):
    credential_id: uuid.UUID
    status: Literal["verified"] = "verified"
    probe_kind: CredentialVerifyProbeKind
    transport_mode: CredentialVerifyTransportMode | None = None
    last_verified_at: datetime
    message: str
