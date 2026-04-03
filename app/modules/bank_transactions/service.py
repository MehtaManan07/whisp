"""Service for processing bank transaction emails."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.integrations.gmail.service import GmailService
from app.integrations.whatsapp.service import WhatsAppService
from app.core.cache.service import CacheService
from app.modules.bank_transactions.dto import (
    ParsedTransactionData,
    ProcessTransactionsResponse,
    PendingTransactionConfirmation,
)
from app.modules.bank_transactions.models import ProcessedBankTransaction
from app.modules.bank_transactions.parser import parse_bank_transaction_email
from app.core.db.engine import run_db

logger = logging.getLogger(__name__)

# Cache keys
LAST_PROCESSED_DATE_KEY = "bank_transactions:last_processed_date"
PENDING_CONFIRMATION_KEY_PREFIX = "bank_transactions:pending:"
DEFAULT_LOOKBACK_DAYS = 7


class BankTransactionService:
    """Service for processing bank transaction emails and sending WhatsApp prompts."""
    
    def __init__(
        self,
        gmail_service: GmailService,
        whatsapp_service: WhatsAppService,
        cache_service: CacheService,
        whatsapp_number: str = "",
    ):
        self.gmail_service = gmail_service
        self.whatsapp_service = whatsapp_service
        self.cache_service = cache_service
        self.whatsapp_number = whatsapp_number

    def _pending_cache_key(self, user_wa_id: str) -> str:
        return f"{PENDING_CONFIRMATION_KEY_PREFIX}{user_wa_id}"
    
    async def _get_pointer_date(self) -> datetime:
        """Get last processed date from cache or use default lookback."""
        cached_date = await self.cache_service.get_key(LAST_PROCESSED_DATE_KEY)
        
        if cached_date:
            try:
                return datetime.fromisoformat(cached_date)
            except (ValueError, TypeError):
                logger.warning(f"Invalid cached date format: {cached_date}")
        
        return datetime.now(timezone.utc) - timedelta(days=DEFAULT_LOOKBACK_DAYS)
    
    async def _update_pointer_date(self, new_date: datetime) -> None:
        """Update last processed date in cache."""
        await self.cache_service.set_key(
            LAST_PROCESSED_DATE_KEY,
            new_date.isoformat(),
            ttl=None,
        )
        logger.debug(f"Updated bank transaction pointer date to: {new_date.isoformat()}")
    
    def _is_transaction_processed_sync(self, db: Session, gmail_message_id: str) -> bool:
        """Check if transaction email was already processed."""
        result = db.execute(
            select(ProcessedBankTransaction.id).where(
                ProcessedBankTransaction.gmail_message_id == gmail_message_id
            )
        )
        return result.scalar_one_or_none() is not None

    def _get_already_processed_ids_sync(self, db: Session, gmail_message_ids: list[str]) -> set[str]:
        """Batch check which email IDs are already processed."""
        if not gmail_message_ids:
            return set()
        result = db.execute(
            select(ProcessedBankTransaction.gmail_message_id).where(
                ProcessedBankTransaction.gmail_message_id.in_(gmail_message_ids)
            )
        )
        return set(result.scalars().all())
    
    def _save_processed_transaction_sync(
        self,
        db: Session,
        gmail_message_id: str,
        parsed_data: ParsedTransactionData,
        whatsapp_sent: bool = False,
    ) -> ProcessedBankTransaction:
        """Save processed transaction to database."""
        transaction = ProcessedBankTransaction(
            gmail_message_id=gmail_message_id,
            bank=parsed_data.bank,
            amount=parsed_data.amount,
            merchant=parsed_data.merchant,
            transaction_date=parsed_data.transaction_date,
            reference_number=parsed_data.reference_number,
            whatsapp_sent=whatsapp_sent,
            user_action=None,
            expense_id=None,
        )
        
        db.add(transaction)
        db.flush()
        
        logger.debug(
            f"Saved processed transaction {gmail_message_id} "
            f"({parsed_data.bank}, ₹{parsed_data.amount})"
        )
        return transaction
    
    async def store_pending_confirmation(
        self,
        gmail_message_id: str,
        user_wa_id: str,
        transaction_data: ParsedTransactionData,
        prompt_message_id: Optional[str] = None,
    ) -> None:
        """Store pending transaction prompt state in cache."""
        confirmation = PendingTransactionConfirmation(
            gmail_message_id=gmail_message_id,
            user_wa_id=user_wa_id,
            prompt_message_id=prompt_message_id,
            transaction_data=transaction_data,
        )

        cache_key = self._pending_cache_key(user_wa_id)
        existing = await self.cache_service.get_key(cache_key)
        pending_items = existing if isinstance(existing, list) else []
        pending_items.append(confirmation.model_dump(mode="json"))

        await self.cache_service.set_key(cache_key, pending_items, ttl=86400)
    
    async def get_pending_confirmation(
        self,
        user_wa_id: str,
        replied_to_message_id: Optional[str] = None,
    ) -> Optional[PendingTransactionConfirmation]:
        """Get a matching pending transaction from cache."""
        pending_items = await self.get_all_pending_confirmations(user_wa_id)
        if not pending_items:
            return None

        if replied_to_message_id:
            for item in pending_items:
                if item.prompt_message_id == replied_to_message_id:
                    logger.debug(
                        "Matched pending transaction via reply context: user=%s prompt=%s",
                        user_wa_id,
                        replied_to_message_id,
                    )
                    return item
            logger.debug(
                "No pending transaction match for reply context: user=%s prompt=%s",
                user_wa_id,
                replied_to_message_id,
            )
            return None

        if len(pending_items) == 1:
            return pending_items[0]
        return None

    async def get_all_pending_confirmations(
        self, user_wa_id: str
    ) -> list[PendingTransactionConfirmation]:
        """Get all pending transactions for a user."""
        cache_key = self._pending_cache_key(user_wa_id)
        cached_data = await self.cache_service.get_key(cache_key)
        if not cached_data:
            return []

        if not isinstance(cached_data, list):
            return []

        pending_items: list[PendingTransactionConfirmation] = []
        for item in cached_data:
            try:
                pending_items.append(PendingTransactionConfirmation.model_validate(item))
            except Exception as e:
                logger.error(f"Error parsing pending transaction item: {e}")
        return pending_items

    async def clear_pending_confirmation(
        self,
        user_wa_id: str,
        gmail_message_id: Optional[str] = None,
        prompt_message_id: Optional[str] = None,
    ) -> None:
        """Clear pending confirmation state from cache."""
        cache_key = self._pending_cache_key(user_wa_id)
        pending_items = await self.get_all_pending_confirmations(user_wa_id)
        if not pending_items:
            return

        if not gmail_message_id and not prompt_message_id:
            await self.cache_service.delete_key(cache_key)
            logger.info(f"Cleared all pending confirmations for {user_wa_id}")
            return

        remaining = []
        for item in pending_items:
            matches_gmail = gmail_message_id and item.gmail_message_id == gmail_message_id
            matches_prompt = prompt_message_id and item.prompt_message_id == prompt_message_id
            if not (matches_gmail or matches_prompt):
                remaining.append(item.model_dump(mode="json"))

        if remaining:
            await self.cache_service.set_key(cache_key, remaining, ttl=86400)
        else:
            await self.cache_service.delete_key(cache_key)

    async def mark_transaction_action(
        self, gmail_message_id: str, action: str, expense_id: Optional[int] = None
    ) -> None:
        """Update processed transaction action state."""

        def _update(db: Session):
            values = {"user_action": action}
            if expense_id is not None:
                values["expense_id"] = expense_id

            db.execute(
                update(ProcessedBankTransaction)
                .where(ProcessedBankTransaction.gmail_message_id == gmail_message_id)
                .values(**values)
            )
            db.commit()

        await run_db(_update)
        logger.info(
            "Marked transaction action: gmail_message_id=%s action=%s expense_id=%s",
            gmail_message_id,
            action,
            expense_id,
        )
    
    def format_transaction_prompt(self, parsed_data: ParsedTransactionData) -> str:
        """Format simple amount-only WhatsApp prompt."""
        amount_str = f"₹{parsed_data.amount:,.2f}"
        return f"Brother, you spent {amount_str} recently. What was this expense about?"
    
    async def process_emails(self, max_results: int = 50) -> ProcessTransactionsResponse:
        """
        Fetch bank transaction emails, parse them, store in DB, and send WhatsApp prompts.
        """
        errors = []
        processed_count = 0
        sent_count = 0
        skipped_count = 0
        latest_email_date: Optional[datetime] = None
        
        pointer_date = await self._get_pointer_date()
        
        logger.debug(
            f"Processing bank transaction emails after: {pointer_date.isoformat()}, "
            f"max_results: {max_results}"
        )
        
        if not self.whatsapp_number:
            logger.warning(
                "BANK_TRANSACTIONS_WHATSAPP_NUMBER is not configured; "
                "transactions will be saved but no WhatsApp prompts will be sent"
            )

        try:
            # Fetch emails filtered by bank senders to avoid missing
            # transaction emails buried under unrelated messages.
            bank_senders = [
                "icicibank.com",
                "hdfcbank.bank.in",
            ]
            emails = []
            for sender in bank_senders:
                fetched = await asyncio.to_thread(
                    self.gmail_service.fetch_emails,
                    from_email=sender,
                    after_date=pointer_date,
                    max_results=max_results,
                    unread_only=True,
                )
                emails.extend(fetched)

            logger.debug(f"Fetched {len(emails)} bank emails to check")

            # Batch dedup: check all email IDs in one query instead of per-email
            email_ids = [e.id for e in emails]
            already_processed_ids = await run_db(
                lambda db: self._get_already_processed_ids_sync(db, email_ids)
            )

            for email in emails:
                try:
                    # Try to parse as bank transaction
                    parsed_data = parse_bank_transaction_email(email)
                    
                    if not parsed_data:
                        # Not a recognized bank transaction email — mark as read
                        # so it doesn't pile up and crowd out real transactions.
                        try:
                            await asyncio.to_thread(self.gmail_service.mark_as_read, email.id)
                        except Exception:
                            pass
                        logger.debug("Email %s skipped: not a supported bank transaction", email.id)
                        continue

                    # Safety guard: only process positive debit-like amounts
                    if parsed_data.amount <= 0:
                        logger.debug(f"Skipping non-positive amount for email {email.id}")
                        continue
                    
                    if email.id in already_processed_ids:
                        logger.debug(f"Skipping already processed transaction: {email.id}")
                        skipped_count += 1
                        continue
                    
                    # Format WhatsApp message
                    message = self.format_transaction_prompt(parsed_data)
                    logger.debug(
                        "Parsed transaction: gmail_message_id=%s bank=%s amount=%.2f",
                        email.id,
                        parsed_data.bank,
                        parsed_data.amount,
                    )
                    
                    # Send WhatsApp prompt
                    whatsapp_sent = False
                    if self.whatsapp_number:
                        try:
                            send_result = await self.whatsapp_service.send_text(
                                self.whatsapp_number,
                                message,
                            )
                            prompt_message_id = None
                            if isinstance(send_result, dict):
                                messages = send_result.get("messages") or []
                                if messages and isinstance(messages[0], dict):
                                    prompt_message_id = messages[0].get("id")

                            sent_count += 1
                            whatsapp_sent = True

                            # Store pending confirmation state
                            await self.store_pending_confirmation(
                                gmail_message_id=email.id,
                                user_wa_id=self.whatsapp_number,
                                transaction_data=parsed_data,
                                prompt_message_id=prompt_message_id,
                            )
                        except Exception as e:
                            error_msg = f"Failed to send WhatsApp for {email.id}: {str(e)}"
                            logger.error(error_msg)
                            errors.append(error_msg)
                    
                    # Save to database BEFORE marking as read so we don't
                    # lose the transaction if the DB write fails.
                    await run_db(
                        lambda db, eid=email.id, pd=parsed_data, ws=whatsapp_sent:
                        self._save_processed_transaction_sync(db, eid, pd, ws)
                    )

                    # Mark email as read so it's not fetched again
                    try:
                        await asyncio.to_thread(self.gmail_service.mark_as_read, email.id)
                    except Exception as e:
                        logger.warning(f"Failed to mark email {email.id} as read: {e}")
                    
                    processed_count += 1
                    
                    # Track latest email date
                    if email.date:
                        if latest_email_date is None or email.date > latest_email_date:
                            latest_email_date = email.date

                except Exception as e:
                    error_msg = f"Error processing email {email.id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            # Advance pointer so we don't re-fetch the same batch.
            # Use the latest email date we saw (even if it wasn't a transaction),
            # falling back to now if we fetched emails but none had dates.
            if emails:
                max_email_date = max(
                    (e.date for e in emails if e.date),
                    default=None,
                )
                advance_to = max_email_date or latest_email_date
                if advance_to and advance_to > pointer_date:
                    await self._update_pointer_date(advance_to)
        
        except Exception as e:
            error_msg = f"Error fetching bank transaction emails: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        logger.info(
            f"Bank transaction processing complete: {processed_count} processed, "
            f"{skipped_count} skipped, {sent_count} sent, {len(errors)} errors"
        )
        
        return ProcessTransactionsResponse(
            processed_count=processed_count,
            sent_count=sent_count,
            errors=errors,
        )
