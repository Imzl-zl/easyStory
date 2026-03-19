from typing import TYPE_CHECKING
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.shared.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.modules.content.models import Content
    from app.modules.user.models import User
    from app.modules.workflow.models import WorkflowExecution


class Project(Base, TimestampMixin, UUIDMixin, SoftDeleteMixin):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255))
    genre: Mapped[str | None] = mapped_column(String(100))
    target_words: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    template_id: Mapped[uuid.UUID | None] = mapped_column()
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    project_setting: Mapped[dict | None] = mapped_column(JSON)
    allow_system_credential_pool: Mapped[bool] = mapped_column(Boolean, default=False)

    owner: Mapped["User"] = relationship(back_populates="projects")
    contents: Mapped[list["Content"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    workflow_executions: Mapped[list["WorkflowExecution"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
