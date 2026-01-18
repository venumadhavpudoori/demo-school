"""Base model classes and mixins for SQLAlchemy models."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TenantMixin:
    """Mixin that adds tenant_id foreign key for multi-tenancy support."""

    @declared_attr
    def tenant_id(cls) -> Mapped[int]:
        return mapped_column(
            Integer,
            ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )


class TenantAwareBase(Base, TimestampMixin, TenantMixin):
    """Abstract base class for tenant-aware models with timestamps.

    All models that belong to a tenant should inherit from this class.
    It automatically includes:
    - tenant_id: Foreign key to tenants table
    - created_at: Timestamp when record was created
    - updated_at: Timestamp when record was last updated
    """

    __abstract__ = True

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={getattr(self, 'id', None)}, tenant_id={self.tenant_id})>"
