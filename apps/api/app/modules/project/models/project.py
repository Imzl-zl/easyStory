from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.types import JSON

from app.modules.project.schemas import extract_project_summary_fields, validate_project_setting
from app.shared.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.modules.content.models import Content
    from app.modules.template.models import Template
    from app.modules.user.models import User
    from app.modules.workflow.models import WorkflowExecution


class Project(Base, TimestampMixin, UUIDMixin, SoftDeleteMixin):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255))
    genre: Mapped[str | None] = mapped_column(String(100))
    target_words: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("templates.id"))
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    project_setting: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    allow_system_credential_pool: Mapped[bool] = mapped_column(Boolean, default=False)

    owner: Mapped["User"] = relationship(back_populates="projects")
    template: Mapped["Template | None"] = relationship(back_populates="projects")
    contents: Mapped[list["Content"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    workflow_executions: Mapped[list["WorkflowExecution"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    @validates("project_setting")
    def _validate_project_setting(self, _: str, value: Any) -> dict[str, Any] | None:
        setting = validate_project_setting(value)
        genre, target_words = extract_project_summary_fields(setting)
        self.genre = genre
        self.target_words = target_words
        return setting
