from app.integrations.gmail.dto import EmailDTO
from app.integrations.gmail.service import GmailService
from app.integrations.gmail.senders import (
    TransactionSender,
    TRANSACTION_SENDERS,
    build_transaction_query,
    bank_for_sender,
)

__all__ = [
    "EmailDTO",
    "GmailService",
    "TransactionSender",
    "TRANSACTION_SENDERS",
    "build_transaction_query",
    "bank_for_sender",
]
