import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
