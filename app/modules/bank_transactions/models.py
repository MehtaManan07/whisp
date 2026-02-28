"""Models for bank transaction processing."""

from datetime import datetime
from sqlalchemy import String, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from app.core.db.base import BaseModel


class ProcessedBankTransaction(BaseModel):
    """Track processed bank transaction emails for idempotency."""
    
    __tablename__ = "processed_bank_transactions"
    
    gmail_message_id: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
        index=True,
        comment="Gmail message ID for deduplication",
    )
    
    bank: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="Bank name (ICICI or HDFC)",
    )
    
    amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Transaction amount",
    )
    
    merchant: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
        comment="Merchant/vendor name",
    )
    
    transaction_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Transaction timestamp",
    )
    
    reference_number: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
        comment="Bank reference number",
    )
    
    whatsapp_sent: Mapped[bool] = mapped_column(
        default=False,
        comment="Whether WhatsApp notification was sent",
    )
    
    user_action: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
        comment="User action: confirmed, dismissed, or None if pending",
    )
    
    expense_id: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Created expense ID if user confirmed",
    )
    
    def __repr__(self) -> str:
        return f"<ProcessedBankTransaction(bank='{self.bank}', amount={self.amount}, merchant='{self.merchant}')>"
