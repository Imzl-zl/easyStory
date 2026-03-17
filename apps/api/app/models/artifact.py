import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class Artifact(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "artifacts"

    node_execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("node_executions.id")
    )
    artifact_type: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    word_count: Mapped[int | None] = mapped_column(Integer)

    node_execution: Mapped["NodeExecution"] = relationship(
        back_populates="artifacts"
    )
