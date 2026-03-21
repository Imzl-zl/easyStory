from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.shared.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.modules.content.models import Content
    from app.modules.project.models import Project


class Analysis(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "analyses"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    content_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contents.id"))
    analysis_type: Mapped[str] = mapped_column(String(50))
    source_title: Mapped[str | None] = mapped_column(String(255))
    analysis_scope: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    result: Mapped[dict[str, Any]] = mapped_column(JSON)
    suggestions: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    generated_skill_key: Mapped[str | None] = mapped_column(String(100))

    project: Mapped["Project"] = relationship(back_populates="analyses")
    content: Mapped["Content | None"] = relationship()
