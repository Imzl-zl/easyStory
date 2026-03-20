from decimal import Decimal
import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db.base import Base, TimestampMixin, UUIDMixin


class TokenUsage(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "token_usages"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    node_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("node_executions.id")
    )
    credential_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("model_credentials.id")
    )
    usage_type: Mapped[str] = mapped_column(String(20))
    model_name: Mapped[str] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(12, 6))
