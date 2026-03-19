from typing import TYPE_CHECKING
import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.shared.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.modules.workflow.models import NodeExecution


class Artifact(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "artifacts"

    node_execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("node_executions.id")
    )
    artifact_type: Mapped[str] = mapped_column(String(50))
    content_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("content_versions.id")
    )
    payload: Mapped[dict | None] = mapped_column(JSON)
    word_count: Mapped[int | None] = mapped_column(Integer)

    node_execution: Mapped["NodeExecution"] = relationship(
        back_populates="artifacts"
    )
