from typing import TYPE_CHECKING
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.shared.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.modules.project.models import Project
    from app.modules.review.models import ReviewAction
    from app.modules.workflow.models import Artifact

ACTIVE_WORKFLOW_FILTER = "status IN ('created', 'running', 'paused')"


class WorkflowExecution(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "workflow_executions"
    __table_args__ = (
        Index(
            "uq_workflow_execution_active_project",
            "project_id",
            unique=True,
            sqlite_where=text(ACTIVE_WORKFLOW_FILTER),
            postgresql_where=text(ACTIVE_WORKFLOW_FILTER),
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    template_id: Mapped[uuid.UUID | None] = mapped_column()
    status: Mapped[str] = mapped_column(String(50), default="created")
    current_node_id: Mapped[str | None] = mapped_column(String(200))
    pause_reason: Mapped[str | None] = mapped_column(String(50))
    resume_from_node: Mapped[str | None] = mapped_column(String(200))
    snapshot: Mapped[dict | None] = mapped_column(JSON)
    workflow_snapshot: Mapped[dict | None] = mapped_column(JSON)
    skills_snapshot: Mapped[dict | None] = mapped_column(JSON)
    agents_snapshot: Mapped[dict | None] = mapped_column(JSON)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped["Project"] = relationship(back_populates="workflow_executions")
    node_executions: Mapped[list["NodeExecution"]] = relationship(
        back_populates="workflow_execution", cascade="all, delete-orphan"
    )


class NodeExecution(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "node_executions"
    __table_args__ = (
        UniqueConstraint(
            "workflow_execution_id", "node_id", "sequence",
            name="uq_node_execution_unique",
        ),
    )

    workflow_execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_executions.id")
    )
    node_id: Mapped[str] = mapped_column(String(200))
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    node_order: Mapped[int] = mapped_column(Integer, default=0)
    node_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), default="pending")
    input_data: Mapped[dict | None] = mapped_column("input", JSON)
    output_data: Mapped[dict | None] = mapped_column("output", JSON)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    workflow_execution: Mapped["WorkflowExecution"] = relationship(
        back_populates="node_executions"
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        back_populates="node_execution", cascade="all, delete-orphan"
    )
    review_actions: Mapped[list["ReviewAction"]] = relationship(
        back_populates="node_execution", cascade="all, delete-orphan"
    )
