import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class Project(Base, TimestampMixin, UUIDMixin, SoftDeleteMixin):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255))
    genre: Mapped[str | None] = mapped_column(String(100))
    target_words: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    template_id: Mapped[uuid.UUID | None] = mapped_column()
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    config: Mapped[dict | None] = mapped_column(JSON)

    owner: Mapped["User"] = relationship(back_populates="projects")
    contents: Mapped[list["Content"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    workflow_executions: Mapped[list["WorkflowExecution"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
