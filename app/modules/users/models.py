from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from app.core.db.base import BaseModel

if TYPE_CHECKING:
    from app.modules.expenses.models import Expense
    from app.modules.reminders.models import Reminder
    from app.modules.budgets.models import Budget


class User(BaseModel):
    """User model for storing user information"""

    __tablename__ = "users"

    wa_id: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
        index=True,
        comment="WhatsApp ID from webhook",
    )

    name: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, comment="Optional, from user input"
    )

    phone_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    timezone: Mapped[Optional[str]] = mapped_column(
        String,
        default="UTC",
        nullable=True,
        comment="User's timezone (IANA timezone name, e.g., 'Asia/Kolkata')",
    )

    last_active: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="For engagement reminders"
    )

    streak: Mapped[int] = mapped_column(
        Integer, default=0, comment="Consecutive log days"
    )

    meta: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships - forward reference to avoid circular imports
    # Changed from lazy="selectin" to lazy="noload" to prevent loading ALL user's data
    # This prevents fetching 1000+ expenses when you just need user info
    # Use explicit selectinload() in queries when you actually need the relationships
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense",
        back_populates="user",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    reminders: Mapped[List["Reminder"]] = relationship(
        "Reminder",
        back_populates="user",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    budgets: Mapped[List["Budget"]] = relationship(
        "Budget",
        back_populates="user",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(wa_id='{self.wa_id}', name='{self.name}')>"
