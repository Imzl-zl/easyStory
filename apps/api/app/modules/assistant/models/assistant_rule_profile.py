from __future__ import annotations

import uuid

from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db.base import Base, TimestampMixin, UUIDMixin


class AssistantRuleProfile(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "assistant_rule_profiles"
    __table_args__ = (
        UniqueConstraint("owner_type", "owner_id", name="uq_assistant_rule_profiles_owner"),
    )

    owner_type: Mapped[str] = mapped_column(String(20))
    owner_id: Mapped[uuid.UUID] = mapped_column()
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    content: Mapped[str] = mapped_column(Text, default="")
