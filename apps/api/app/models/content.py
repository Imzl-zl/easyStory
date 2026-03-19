import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .base import Base, TimestampMixin, UUIDMixin

CHAPTER_CONSTRAINT = """
(
  content_type = 'chapter'
  AND chapter_number IS NOT NULL
  AND chapter_number > 0
)
OR (
  content_type IN ('outline', 'opening_plan')
  AND chapter_number IS NULL
)
"""
CHAPTER_FILTER = "content_type = 'chapter'"
OUTLINE_FILTER = "content_type = 'outline'"
OPENING_PLAN_FILTER = "content_type = 'opening_plan'"
CURRENT_TRUE_SQLITE = "is_current = 1"
CURRENT_TRUE_POSTGRES = "is_current = true"
BEST_TRUE_SQLITE = "is_best = 1"
BEST_TRUE_POSTGRES = "is_best = true"


class Content(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "contents"
    __table_args__ = (
        CheckConstraint(CHAPTER_CONSTRAINT, name="ck_contents_chapter_number_by_type"),
        Index(
            "uq_contents_project_outline",
            "project_id",
            unique=True,
            sqlite_where=text(OUTLINE_FILTER),
            postgresql_where=text(OUTLINE_FILTER),
        ),
        Index(
            "uq_contents_project_opening_plan",
            "project_id",
            unique=True,
            sqlite_where=text(OPENING_PLAN_FILTER),
            postgresql_where=text(OPENING_PLAN_FILTER),
        ),
        Index(
            "uq_contents_project_chapter_number",
            "project_id",
            "chapter_number",
            unique=True,
            sqlite_where=text(CHAPTER_FILTER),
            postgresql_where=text(CHAPTER_FILTER),
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contents.id"))
    content_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    chapter_number: Mapped[int | None] = mapped_column(Integer)
    order_index: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    last_edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped["Project"] = relationship(back_populates="contents")
    versions: Mapped[list["ContentVersion"]] = relationship(
        back_populates="content_ref", cascade="all, delete-orphan"
    )


class ContentVersion(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "content_versions"
    __table_args__ = (
        UniqueConstraint("content_id", "version_number", name="uq_content_versions_version_number"),
        Index(
            "uq_content_versions_current_true",
            "content_id",
            unique=True,
            sqlite_where=text(CURRENT_TRUE_SQLITE),
            postgresql_where=text(CURRENT_TRUE_POSTGRES),
        ),
        Index(
            "uq_content_versions_best_true",
            "content_id",
            unique=True,
            sqlite_where=text(BEST_TRUE_SQLITE),
            postgresql_where=text(BEST_TRUE_POSTGRES),
        ),
    )

    content_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contents.id"))
    version_number: Mapped[int] = mapped_column(Integer)
    content_text: Mapped[str] = mapped_column("content_text", Text)
    created_by: Mapped[str] = mapped_column(String(50), default="system")
    word_count: Mapped[int | None] = mapped_column(Integer)
    change_summary: Mapped[str | None] = mapped_column(Text)
    change_source: Mapped[str] = mapped_column(String(50), default="ai_generate")
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    is_best: Mapped[bool] = mapped_column(Boolean, default=False)
    context_snapshot_hash: Mapped[str | None] = mapped_column(String(64))
    ai_conversation_id: Mapped[uuid.UUID | None] = mapped_column()

    content_ref: Mapped["Content"] = relationship(back_populates="versions")
