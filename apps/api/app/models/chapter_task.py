import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from .base import Base, TimestampMixin, UUIDMixin


class ChapterTask(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "chapter_tasks"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    chapter_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    brief: Mapped[str] = mapped_column(Text)
    key_characters: Mapped[dict | None] = mapped_column(JSON)
    key_events: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    content_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contents.id"))
