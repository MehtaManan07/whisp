from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import ForeignKey, String, Float, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import BaseModel
from app.utils.datetime import utc_now

if TYPE_CHECKING:
    from app.core.db import User, Category


class Expense(BaseModel):
    __tablename__ = "expenses"
    __table_args__ = (
        # Indexes for query performance
        Index('idx_expenses_timestamp', 'timestamp'),
        Index('idx_expenses_vendor', 'vendor'),
        Index('idx_expenses_deleted_at', 'deleted_at'),
        Index('idx_expenses_user_timestamp', 'user_id', 'timestamp'),
    )

    # Foreign key relationships using integer IDs from BaseModel
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )

    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True, index=True
    )

    # Expense fields
    amount: Mapped[float] = mapped_column(Float, nullable=False)

    note: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    source_message_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, index=True
    )

    # Relationships
    # Changed from lazy="selectin" to lazy="noload" to prevent automatic loading
    # Use explicit selectinload() in queries when needed
    user: Mapped["User"] = relationship(
        "User", back_populates="expenses", lazy="noload"
    )

    category: Mapped[Optional["Category"]] = relationship(
        "Category", back_populates="expenses", lazy="noload"
    )

    vendor: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    def __repr__(self) -> str:
        return f"<Expense(amount={self.amount}, user_id='{self.user_id}')>"
