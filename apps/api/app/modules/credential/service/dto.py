from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.shared.runtime.llm_protocol import LlmApiDialect, LlmAuthStrategy

CredentialOwnerType = Literal["system", "user", "project"]
CredentialExtraHeaders = dict[str, str]


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
    auth_strategy: LlmAuthStrategy | None = None
    api_key_header_name: str | None = Field(default=None, max_length=100)
    extra_headers: CredentialExtraHeaders | None = None


class CredentialUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_dialect: LlmApiDialect | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    api_key: str | None = Field(default=None, min_length=1, max_length=500)
    base_url: str | None = Field(default=None, max_length=500)
    default_model: str | None = Field(default=None, min_length=1, max_length=100)
    auth_strategy: LlmAuthStrategy | None = None
    api_key_header_name: str | None = Field(default=None, max_length=100)
    extra_headers: CredentialExtraHeaders | None = None


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
    auth_strategy: LlmAuthStrategy | None
    api_key_header_name: str | None
    extra_headers: CredentialExtraHeaders | None
    is_active: bool
    last_verified_at: datetime | None


class CredentialVerifyResultDTO(BaseModel):
    credential_id: uuid.UUID
    status: Literal["verified"] = "verified"
    last_verified_at: datetime
    message: str
