from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, DateTime, Boolean, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import BaseModel

if TYPE_CHECKING:
    from typing import List


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
    # Legacy single-item fields (deprecated, use items relationship)
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

    # Relationship to order items
    items: Mapped[list["DeodapOrderItem"]] = relationship(
        "DeodapOrderItem", back_populates="order_email", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"<DeodapOrderEmail(id={self.id}, order_id={self.order_id}, "
            f"gmail_message_id={self.gmail_message_id})>"
        )


class DeodapOrderItem(BaseModel):
    """Model for storing individual order items from Deodap/Kraftculture orders."""

    __tablename__ = "deodap_order_items"

    # Foreign key to order email
    order_email_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("deodap_order_emails.id"), nullable=False, index=True
    )

    # Item fields
    product_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sku: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    price: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quantity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Relationship back to order email
    order_email: Mapped["DeodapOrderEmail"] = relationship(
        "DeodapOrderEmail", back_populates="items"
    )

    def __repr__(self):
        return (
            f"<DeodapOrderItem(id={self.id}, order_email_id={self.order_email_id}, "
            f"product_name={self.product_name}, sku={self.sku})>"
        )
