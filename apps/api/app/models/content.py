import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .base import Base, TimestampMixin, UUIDMixin


class Content(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "contents"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contents.id"))
    content_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    chapter_number: Mapped[int | None] = mapped_column(Integer)
    order_index: Mapped[int | None] = mapped_column(Integer)
    content: Mapped[str | None] = mapped_column(Text)
    word_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    last_edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped["Project"] = relationship(back_populates="contents")
    versions: Mapped[list["ContentVersion"]] = relationship(
        back_populates="content_ref", cascade="all, delete-orphan"
    )


class ContentVersion(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "content_versions"

    content_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contents.id"))
    version_number: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    word_count: Mapped[int | None] = mapped_column(Integer)
    change_summary: Mapped[str | None] = mapped_column(Text)
    change_source: Mapped[str] = mapped_column(String(50), default="system")
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    is_best: Mapped[bool] = mapped_column(Boolean, default=False)
    context_snapshot_hash: Mapped[str | None] = mapped_column(String(64))
    ai_conversation_id: Mapped[uuid.UUID | None] = mapped_column()

    content_ref: Mapped["Content"] = relationship(back_populates="versions")
