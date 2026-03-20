from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AuthRegisterDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=200)
    email: str | None = Field(default=None, max_length=200)


class AuthLoginDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=200)


class AuthTokenDTO(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user_id: uuid.UUID
    username: str
