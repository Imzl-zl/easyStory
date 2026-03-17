import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .base import Base, TimestampMixin, UUIDMixin


class ReviewAction(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "review_actions"

    node_execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("node_executions.id")
    )
    agent_id: Mapped[str] = mapped_column(String(100))
    review_type: Mapped[str] = mapped_column(String(100))
    result: Mapped[str] = mapped_column(String(50))
    issues: Mapped[dict | None] = mapped_column(JSON)

    node_execution: Mapped["NodeExecution"] = relationship(
        back_populates="review_actions"
    )
