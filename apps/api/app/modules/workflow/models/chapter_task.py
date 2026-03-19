import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.shared.db.base import Base, TimestampMixin, UUIDMixin


class ChapterTask(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "chapter_tasks"
    __table_args__ = (
        UniqueConstraint(
            "workflow_execution_id",
            "chapter_number",
            name="uq_chapter_task_plan",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    workflow_execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_executions.id")
    )
    chapter_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    brief: Mapped[str] = mapped_column(Text)
    key_characters: Mapped[list[str] | None] = mapped_column(JSON)
    key_events: Mapped[list[str] | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    content_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contents.id"))
