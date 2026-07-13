from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CapturedTransactionData(BaseModel):
    """Detached, serializable view of a CapturedTransaction row."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    gmail_message_id: str
    bank: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = "INR"
    card_last4: Optional[str] = None
    merchant_hint: Optional[str] = None
    raw_subject: Optional[str] = None
    transaction_date: Optional[datetime] = None
    status: str
    expense_id: Optional[int] = None
    telegram_chat_id: Optional[str] = None
    telegram_message_id: Optional[str] = None
    last_nudged_at: Optional[datetime] = None


class CreateCapturedTransaction(BaseModel):
    """Input for persisting a newly captured transaction."""

    user_id: int
    gmail_message_id: str = Field(..., description="Gmail message id (dedup key)")
    bank: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = "INR"
    card_last4: Optional[str] = None
    merchant_hint: Optional[str] = None
    raw_subject: Optional[str] = None
    transaction_date: Optional[datetime] = None
    status: str = "awaiting_description"
