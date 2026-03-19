from typing import TYPE_CHECKING
import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.shared.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.modules.workflow.models import NodeExecution


class ReviewAction(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "review_actions"

    node_execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("node_executions.id")
    )
    agent_id: Mapped[str] = mapped_column(String(100))
    reviewer_name: Mapped[str | None] = mapped_column(String(255))
    review_type: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50))
    score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    summary: Mapped[str | None] = mapped_column(Text)
    issues: Mapped[dict | None] = mapped_column(JSON)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)
    tokens_used: Mapped[int | None] = mapped_column(Integer)

    node_execution: Mapped["NodeExecution"] = relationship(
        back_populates="review_actions"
    )
