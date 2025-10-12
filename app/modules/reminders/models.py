from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from sqlalchemy import ForeignKey, Numeric, String, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.utils.datetime import utc_now


from app.core.db.base import BaseModel


class Reminder(BaseModel):
    """Model for storing user reminders with recurrence support."""

    __tablename__ = "reminders"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reminder_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    # Recurrence configuration
    recurrence_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # once, daily, weekly, monthly, yearly
    recurrence_config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)  # Additional recurrence parameters

    # Scheduling
    next_trigger_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="reminders")
    category = relationship("Category", foreign_keys=[category_id])

    def __repr__(self):
        return (
            f"<Reminder(id={self.id}, type={self.reminder_type}, title={self.title})>"
        )

    @property
    def is_due(self) -> bool:
        """Check if reminder is due for triggering."""
        if not self.is_active:
            return False
        return utc_now() >= self.next_trigger_at

    @property
    def is_recurring(self) -> bool:
        """Check if reminder has recurring schedule."""
        return self.recurrence_type != "once"
