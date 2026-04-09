import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db.base import Base, TimestampMixin, UUIDMixin


class ModelCredential(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "model_credentials"

    owner_type: Mapped[str] = mapped_column(String(20))
    owner_id: Mapped[uuid.UUID | None] = mapped_column()
    provider: Mapped[str] = mapped_column(String(50))
    api_dialect: Mapped[str] = mapped_column(String(50), default="openai_chat_completions")
    display_name: Mapped[str] = mapped_column(String(100))
    encrypted_key: Mapped[str] = mapped_column(Text)
    base_url: Mapped[str | None] = mapped_column(String(500))
    default_model: Mapped[str | None] = mapped_column(String(100))
    interop_profile: Mapped[str | None] = mapped_column(String(80))
    verified_probe_kind: Mapped[str | None] = mapped_column(String(40))
    stream_tool_verified_probe_kind: Mapped[str | None] = mapped_column(String(40))
    stream_tool_last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    buffered_tool_verified_probe_kind: Mapped[str | None] = mapped_column(String(40))
    buffered_tool_last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    context_window_tokens: Mapped[int | None] = mapped_column(Integer)
    default_max_output_tokens: Mapped[int | None] = mapped_column(Integer)
    auth_strategy: Mapped[str | None] = mapped_column(String(50))
    api_key_header_name: Mapped[str | None] = mapped_column(String(100))
    extra_headers: Mapped[dict[str, str] | None] = mapped_column(JSON)
    user_agent_override: Mapped[str | None] = mapped_column(String(300))
    client_name: Mapped[str | None] = mapped_column(String(100))
    client_version: Mapped[str | None] = mapped_column(String(50))
    runtime_kind: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
