"""Cache model for SQLAlchemy"""
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from app.core.db.base import Base


class Cache(Base):
    """Cache table for key-value storage with TTL support"""

    __tablename__ = "cache"

    key: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP")

    __table_args__ = (
        Index('idx_expires_at', 'expires_at'),
    )

    def __repr__(self) -> str:
        return f"<Cache(key={self.key})>"
