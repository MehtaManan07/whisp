from datetime import datetime
from sqlalchemy import DateTime, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Optional
import uuid
from app.utils.datetime import utc_now


class Base(DeclarativeBase):
    """Base class for all database models"""

    pass


class BaseModel(Base):
    """
    Abstract base model that provides common fields for all entities.
    Similar to TypeORM's BaseEntity but with SQLAlchemy 2.0 style.
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("(CURRENT_TIMESTAMP)"), nullable=False
    )

    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=utc_now, nullable=True
    )
    
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
