import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.shared.db.base import Base, TimestampMixin, UUIDMixin


class Export(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "exports"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    format: Mapped[str] = mapped_column(String(20))
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int | None] = mapped_column(Integer)
    config_snapshot: Mapped[dict | None] = mapped_column(JSON)
