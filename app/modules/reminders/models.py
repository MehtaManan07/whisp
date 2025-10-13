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

    def to_human_message(self) -> str:
        """
        Returns a human-readable, natural language summary of the reminder.
        """
        parts = []

        # Start with the title
        main = f"📌 {self.title}"
        parts.append(main)

        # Add reminder type icon
        type_icons = {
            "bill": "💰",
            "expense_log": "📝",
            "custom": "⏰"
        }
        icon = type_icons.get(self.reminder_type, "⏰")

        # Add amount if present (for bills)
        if self.amount:
            parts.append(f"{icon} Amount: ₹{self.amount:,.2f}")

        # Add description if present
        if self.description:
            parts.append(f"📋 {self.description}")

        # Add next trigger time
        from app.utils.datetime import format_relative_time
        trigger_str = format_relative_time(self.next_trigger_at)
        parts.append(f"⏰ Next: {trigger_str}")

        # Add recurrence info
        if self.is_recurring:
            recurrence_display = {
                "daily": "Daily",
                "weekly": "Weekly",
                "monthly": "Monthly",
                "yearly": "Yearly"
            }
            recurrence = recurrence_display.get(self.recurrence_type, self.recurrence_type)
            parts.append(f"🔄 {recurrence}")

        # Add status
        status = "✅ Active" if self.is_active else "⏸️ Inactive"
        parts.append(status)

        return "\n".join(parts)
