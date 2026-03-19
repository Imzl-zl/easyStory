from __future__ import annotations

from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.shared.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.modules.project.models import Project
    from app.modules.workflow.models import WorkflowExecution


class Template(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "templates"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    genre: Mapped[str | None] = mapped_column(String(100))
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)

    nodes: Mapped[list["TemplateNode"]] = relationship(
        back_populates="template", cascade="all, delete-orphan"
    )
    projects: Mapped[list["Project"]] = relationship(back_populates="template")
    workflow_executions: Mapped[list["WorkflowExecution"]] = relationship(
        back_populates="template"
    )


class TemplateNode(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "template_nodes"
    __table_args__ = (
        UniqueConstraint("template_id", "node_order", name="uq_template_node_order"),
    )

    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("templates.id"))
    node_order: Mapped[int] = mapped_column(Integer)
    node_type: Mapped[str] = mapped_column(String(50))
    skill_id: Mapped[str] = mapped_column(String(100))
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    position_x: Mapped[int | None] = mapped_column(Integer)
    position_y: Mapped[int | None] = mapped_column(Integer)
    ui_config: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    template: Mapped["Template"] = relationship(back_populates="nodes")
