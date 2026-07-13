from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import BaseModel


# Lifecycle of a captured transaction.
STATUS_AWAITING = "awaiting_description"  # prompt sent, waiting for user's reply
STATUS_LOGGED = "logged"                  # user described it; expense created
STATUS_DISMISSED = "dismissed"            # user said skip/ignore; never logged
STATUS_IGNORED = "ignored"                # non-debit (OTP/credit/decline), auto-skipped


class CapturedTransaction(BaseModel):
    """
    A charge detected from a bank/card email. We store the reliable bits
    (amount, bank, time) and ask the user to describe it; the expense is created
    only from the user's description.

    ``gmail_message_id`` is unique — the dedup key, so an email is never
    processed twice regardless of status.
    """

    __tablename__ = "captured_transactions"
    __table_args__ = (
        Index("idx_captured_txn_status", "status"),
        Index("idx_captured_txn_user", "user_id"),
        Index("idx_captured_txn_tg_msg", "telegram_message_id"),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )

    gmail_message_id: Mapped[str] = mapped_column(
        String, nullable=False, unique=True, index=True
    )

    bank: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="INR")
    card_last4: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Raw merchant string from the email — shown only as a memory hint, never
    # used as the final vendor (it's often messy/aggregator noise).
    merchant_hint: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    raw_subject: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    transaction_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    status: Mapped[str] = mapped_column(
        String, nullable=False, default=STATUS_AWAITING, index=True
    )

    expense_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Telegram prompt bubble the user replies to (reply-threading correlation).
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    telegram_message_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, index=True
    )

    # Last time we nudged the user about this pending capture.
    last_nudged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<CapturedTransaction(id={self.id}, amount={self.amount}, "
            f"status={self.status!r})>"
        )


class CaptureState(BaseModel):
    """
    Per-user Gmail discovery checkpoint (high-water-mark).

    ``gmail_last_checked_epoch`` is the newest email internalDate (epoch seconds)
    we've processed; the next poll queries ``after:<this>`` so downtime never
    creates a discovery gap.
    """

    __tablename__ = "capture_state"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, unique=True, index=True
    )

    gmail_last_checked_epoch: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
