import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from .base import Base, TimestampMixin, UUIDMixin


class ExecutionLog(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "execution_logs"

    workflow_execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_executions.id")
    )
    node_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("node_executions.id")
    )
    level: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    details: Mapped[dict | None] = mapped_column(JSON)


class PromptReplay(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "prompt_replays"

    node_execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("node_executions.id")
    )
    replay_type: Mapped[str] = mapped_column(String(50))
    model_name: Mapped[str] = mapped_column(String(100))
    prompt_text: Mapped[str] = mapped_column(Text)
    response_text: Mapped[str | None] = mapped_column(Text)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
