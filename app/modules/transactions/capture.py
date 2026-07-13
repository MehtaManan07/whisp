"""
Gmail → expense capture pipeline (reply-based).

Discovery uses a persisted high-water-mark (``after:<checkpoint>``) so poller
downtime never creates a gap. We store only the reliable bits from the email
(amount, bank, time) and ask the user to describe the charge; the expense itself
is created from the user's reply (see completion.py). Nothing is auto-logged.
"""

import logging
from typing import Optional

from app.core.config import config
from app.integrations.gmail.service import GmailService
from app.integrations.llm.service import LLMService
from app.intelligence.extraction.txn_extractor import extract_transaction_from_email
from app.modules.transactions.dto import CreateCapturedTransaction
from app.modules.transactions.models import STATUS_AWAITING, STATUS_IGNORED
from app.modules.transactions.service import TransactionsService
from app.modules.users.models import User
from app.modules.users.service import UsersService
from app.utils.datetime import format_datetime_for_user

logger = logging.getLogger(__name__)

# If more than this many captures are pending, nudge with a summary instead of
# re-sending every individual bubble.
NUDGE_BUBBLE_CAP = 5


class GmailExpenseCapture:
    def __init__(
        self,
        gmail_service: GmailService,
        llm_service: LLMService,
        transactions_service: TransactionsService,
        users_service: UsersService,
        telegram_service,
    ):
        self.gmail = gmail_service
        self.llm = llm_service
        self.txns = transactions_service
        self.users = users_service
        self.telegram = telegram_service

    async def _resolve_user(self) -> Optional[User]:
        allowed = config.telegram_allowed_user_id
        if allowed:
            user = await self.users.get_user_by_telegram_id(str(allowed))
            if user:
                return user
            logger.warning("Capture: no user row for TELEGRAM_ALLOWED_USER_ID=%s", allowed)
        users = await self.users.get_all_users(limit=1)
        return users[0] if users else None

    # -------------------------------------------------------------------------
    # Discovery poll
    # -------------------------------------------------------------------------

    async def run(self) -> dict:
        user = await self._resolve_user()
        if not user or not user.telegram_id:
            logger.debug("Capture: no target user with telegram_id; skipping")
            return {"captured": 0, "ignored": 0, "skipped": 0}

        checkpoint = await self.txns.get_checkpoint(user.id)
        # Small overlap to avoid boundary misses; dedup protects against repeats.
        after_epoch = (checkpoint - 60) if checkpoint else None

        emails = await self.gmail.fetch_transaction_emails(
            newer_than_days=config.gmail_lookback_days,
            after_epoch=after_epoch,
        )

        captured = ignored = skipped = 0
        max_internal = checkpoint or 0

        for email in emails:
            if email.internal_date:
                max_internal = max(max_internal, email.internal_date)

            if await self.txns.is_processed(email.id):
                skipped += 1
                continue

            bank = self.gmail.resolve_bank(email.from_email) or email.from_name or "Bank"
            extracted = await extract_transaction_from_email(email, bank, self.llm)
            if extracted is None:
                skipped += 1
                continue

            if not extracted.is_loggable_expense:
                await self.txns.create(
                    CreateCapturedTransaction(
                        user_id=user.id,
                        gmail_message_id=email.id,
                        bank=bank,
                        amount=extracted.amount,
                        currency=extracted.currency,
                        card_last4=extracted.card_last4,
                        merchant_hint=extracted.vendor,
                        raw_subject=email.subject,
                        transaction_date=extracted.transaction_datetime,
                        status=STATUS_IGNORED,
                    )
                )
                await self.gmail.mark_as_read(email.id)
                ignored += 1
                continue

            record = await self.txns.create(
                CreateCapturedTransaction(
                    user_id=user.id,
                    gmail_message_id=email.id,
                    bank=bank,
                    amount=extracted.amount,
                    currency=extracted.currency or "INR",
                    card_last4=extracted.card_last4,
                    merchant_hint=extracted.vendor,
                    raw_subject=email.subject,
                    transaction_date=extracted.transaction_datetime,
                    status=STATUS_AWAITING,
                )
            )
            await self._send_prompt(record, user)
            await self.gmail.mark_as_read(email.id)
            captured += 1

        # Advance the checkpoint past everything we fetched (all are persisted now).
        if max_internal and max_internal != (checkpoint or 0):
            await self.txns.set_checkpoint(user.id, max_internal)

        if captured or ignored:
            logger.info(
                "Capture cycle: %d captured, %d ignored, %d skipped",
                captured,
                ignored,
                skipped,
            )
        return {"captured": captured, "ignored": ignored, "skipped": skipped}

    # -------------------------------------------------------------------------
    # Daily nudge for un-described captures
    # -------------------------------------------------------------------------

    async def nudge_pending(self) -> dict:
        user = await self._resolve_user()
        if not user or not user.telegram_id:
            return {"nudged": 0}

        pending = await self.txns.get_pending(user.id)
        if not pending:
            return {"nudged": 0}

        tz = self.users.get_user_timezone(user)

        if len(pending) > NUDGE_BUBBLE_CAP:
            total = sum(p.amount or 0 for p in pending)
            text = (
                f"📥 You have *{len(pending)}* charges (₹{total:,.0f}) waiting to be "
                f"described. Reply to any of their messages above with what they were."
            )
            try:
                await self.telegram.send_text(to=str(user.telegram_id), text=text)
            except Exception as e:
                logger.error("Nudge summary failed: %s", e)
            return {"nudged": len(pending)}

        nudged = 0
        for record in pending:
            if await self._send_prompt(record, user, tz=tz, is_nudge=True):
                nudged += 1
        return {"nudged": nudged}

    # -------------------------------------------------------------------------
    # Prompt rendering / sending
    # -------------------------------------------------------------------------

    async def _send_prompt(
        self, record, user: User, tz: Optional[str] = None, is_nudge: bool = False
    ) -> bool:
        tz = tz or self.users.get_user_timezone(user)
        text = self._format_prompt(record, tz, is_nudge=is_nudge)
        try:
            resp = await self.telegram.send_text(to=str(user.telegram_id), text=text)
            result = resp.get("result", {}) if isinstance(resp, dict) else {}
            message_id = result.get("message_id")
            chat = result.get("chat", {}) or {}
            chat_id = chat.get("id", user.telegram_id)
            if message_id is not None:
                # Point reply-correlation at the latest bubble.
                await self.txns.set_telegram_message(
                    record.id, str(chat_id), str(message_id)
                )
            else:
                await self.txns.touch_nudged(record.id)
            return True
        except Exception as e:
            logger.error("Capture: failed to send prompt for txn %s: %s", record.id, e)
            return False

    @staticmethod
    def _format_prompt(record, user_timezone: str, is_nudge: bool = False) -> str:
        amount = f"₹{record.amount:,.2f}" if record.amount is not None else "A charge"
        card = f" ··{record.card_last4}" if record.card_last4 else ""
        header = f"💳 *{amount}* on your *{record.bank or 'card'}*{card}"

        meta = []
        if record.transaction_date:
            meta.append(
                format_datetime_for_user(
                    record.transaction_date, user_timezone, "%b %d, %Y at %I:%M %p"
                )
            )
        if record.merchant_hint:
            meta.append(f"merchant: {record.merchant_hint}")
        meta_line = f"\n🕒 {' · '.join(meta)}" if meta else ""

        prefix = "⏳ Still pending — " if is_nudge else ""
        ask = (
            f"\n\n{prefix}*Reply to this message* with what it was "
            f'(e.g. "swiggy dinner"), or "skip" to ignore.'
        )
        return f"{header}{meta_line}{ask}"
