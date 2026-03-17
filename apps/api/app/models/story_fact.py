import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class StoryFact(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "story_facts"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    chapter_number: Mapped[int] = mapped_column(Integer)
    source_content_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_versions.id")
    )
    fact_type: Mapped[str] = mapped_column(String(50))
    subject: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column()
