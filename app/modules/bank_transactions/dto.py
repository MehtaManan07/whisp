"""DTOs for bank transaction processing."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ParsedTransactionData(BaseModel):
    """Parsed transaction data from email."""
    amount: float
    merchant: Optional[str] = None
    transaction_date: Optional[datetime] = None
    reference_number: Optional[str] = None
    card_last4: Optional[str] = None
    bank: str  # "ICICI" or "HDFC"
    raw_info: Optional[str] = None


class PendingTransactionConfirmation(BaseModel):
    """State for pending transaction confirmation."""
    gmail_message_id: str
    user_wa_id: str
    prompt_message_id: Optional[str] = None
    transaction_data: ParsedTransactionData
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    
class ProcessTransactionsResponse(BaseModel):
    """Response from processing transaction emails."""
    processed_count: int
    sent_count: int
    errors: List[str]
