"""Controller for bank transaction endpoints."""

from fastapi import APIRouter, Depends
from app.modules.bank_transactions.service import BankTransactionService
from app.modules.bank_transactions.dto import ProcessTransactionsResponse
from app.core.dependencies import get_bank_transaction_service

router = APIRouter(prefix="/bank-transactions", tags=["bank-transactions"])


@router.post("/process", response_model=ProcessTransactionsResponse)
async def process_bank_transactions(
    service: BankTransactionService = Depends(get_bank_transaction_service),
) -> ProcessTransactionsResponse:
    """
    Manually trigger bank transaction email processing.
    Useful for testing or manual runs.
    """
    return await service.process_emails()
