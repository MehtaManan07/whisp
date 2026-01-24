from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import BaseModel


class DeodapOrderEmail(BaseModel):
    """Model for storing parsed order emails from Deodap/Kraftculture."""

    __tablename__ = "deodap_order_emails"

    # Gmail reference (unique to prevent duplicates)
    gmail_message_id: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    gmail_thread_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )

    # Email metadata
    email_subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    email_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    email_from: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Parsed order fields
    order_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    order_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    product_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sku: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    price: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quantity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    payment_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    address_line: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    city_state_pincode: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Processing metadata
    whatsapp_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return (
            f"<DeodapOrderEmail(id={self.id}, order_id={self.order_id}, "
            f"gmail_message_id={self.gmail_message_id})>"
        )
