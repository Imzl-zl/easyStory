from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.modules.project.models import Project


class User(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(100), unique=True)
    email: Mapped[str | None] = mapped_column(String(200))
    hashed_password: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    projects: Mapped[list["Project"]] = relationship(back_populates="owner")
