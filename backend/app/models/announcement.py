"""Announcement model for school-wide communications."""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantAwareBase

if TYPE_CHECKING:
    from app.models.user import User


class TargetAudience(str, enum.Enum):
    """Target audience for announcements."""

    ALL = "all"
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"


class Announcement(TenantAwareBase):
    """Announcement model for school-wide communications."""

    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    target_audience: Mapped[TargetAudience] = mapped_column(
        Enum(TargetAudience), default=TargetAudience.ALL, nullable=False
    )
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    author: Mapped["User | None"] = relationship("User", back_populates="announcements")

    def __repr__(self) -> str:
        return f"<Announcement(id={self.id}, title='{self.title}', audience='{self.target_audience.value}')>"
