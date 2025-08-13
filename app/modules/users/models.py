from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from app.core.db.base import BaseModel

if TYPE_CHECKING:
    from app.core.db import Expense


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

    last_active: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="For engagement reminders"
    )

    streak: Mapped[int] = mapped_column(
        Integer, default=0, comment="Consecutive log days"
    )

    meta: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Relationships - forward reference to avoid circular imports
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense",
        back_populates="user",
        lazy="selectin",  # Efficient loading strategy
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(wa_id='{self.wa_id}', name='{self.name}')>"
