from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db.base import Base, TimestampMixin, UUIDMixin


class AssistantUserPreferences(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "assistant_user_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_assistant_user_preferences_user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    default_provider: Mapped[str | None] = mapped_column(String(50))
    default_model_name: Mapped[str | None] = mapped_column(String(100))
