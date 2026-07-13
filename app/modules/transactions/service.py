import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db.engine import run_db
from app.modules.transactions.dto import (
    CapturedTransactionData,
    CreateCapturedTransaction,
)
from app.modules.transactions.models import (
    STATUS_AWAITING,
    STATUS_DISMISSED,
    STATUS_LOGGED,
    CapturedTransaction,
    CaptureState,
)
from app.utils.datetime import utc_now

logger = logging.getLogger(__name__)


class TransactionsService:
    """Persistence for captured (email-sourced) transactions + discovery checkpoint."""

    # ---- dedup / create -----------------------------------------------------

    async def is_processed(self, gmail_message_id: str) -> bool:
        def _check(db: Session) -> bool:
            row = db.scalar(
                select(CapturedTransaction.id).where(
                    CapturedTransaction.gmail_message_id == gmail_message_id
                )
            )
            return row is not None

        return await run_db(_check)

    async def create(self, data: CreateCapturedTransaction) -> CapturedTransactionData:
        def _create(db: Session) -> CapturedTransactionData:
            row = CapturedTransaction(
                user_id=data.user_id,
                gmail_message_id=data.gmail_message_id,
                bank=data.bank,
                amount=data.amount,
                currency=data.currency,
                card_last4=data.card_last4,
                merchant_hint=data.merchant_hint,
                raw_subject=data.raw_subject,
                transaction_date=data.transaction_date,
                status=data.status,
                created_at=utc_now(),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return CapturedTransactionData.model_validate(row)

        return await run_db(_create)

    # ---- lookups ------------------------------------------------------------

    async def get(self, txn_id: int) -> Optional[CapturedTransactionData]:
        def _get(db: Session) -> Optional[CapturedTransactionData]:
            row = db.get(CapturedTransaction, txn_id)
            return CapturedTransactionData.model_validate(row) if row else None

        return await run_db(_get)

    async def get_by_telegram_message_id(
        self, telegram_message_id: str
    ) -> Optional[CapturedTransactionData]:
        def _get(db: Session) -> Optional[CapturedTransactionData]:
            row = db.scalar(
                select(CapturedTransaction).where(
                    CapturedTransaction.telegram_message_id == str(telegram_message_id)
                )
            )
            return CapturedTransactionData.model_validate(row) if row else None

        return await run_db(_get)

    async def get_pending(
        self, user_id: int, limit: int = 50
    ) -> list[CapturedTransactionData]:
        """Awaiting-description captures, oldest first (for nudges / fallback)."""
        def _get(db: Session) -> list[CapturedTransactionData]:
            rows = db.scalars(
                select(CapturedTransaction)
                .where(
                    CapturedTransaction.user_id == user_id,
                    CapturedTransaction.status == STATUS_AWAITING,
                )
                .order_by(CapturedTransaction.transaction_date.asc())
                .limit(limit)
            ).all()
            return [CapturedTransactionData.model_validate(r) for r in rows]

        return await run_db(_get)

    # ---- mutations ----------------------------------------------------------

    async def set_telegram_message(
        self, txn_id: int, chat_id: str, message_id: str
    ) -> None:
        def _update(db: Session) -> None:
            row = db.get(CapturedTransaction, txn_id)
            if row is None:
                return
            row.telegram_chat_id = str(chat_id)
            row.telegram_message_id = str(message_id)
            row.last_nudged_at = utc_now()
            db.commit()

        await run_db(_update)

    async def touch_nudged(self, txn_id: int) -> None:
        def _update(db: Session) -> None:
            row = db.get(CapturedTransaction, txn_id)
            if row is None:
                return
            row.last_nudged_at = utc_now()
            db.commit()

        await run_db(_update)

    async def mark_logged(self, txn_id: int, expense_id: Optional[int] = None) -> None:
        await self._set_status(txn_id, STATUS_LOGGED, expense_id=expense_id)

    async def mark_dismissed(self, txn_id: int) -> None:
        await self._set_status(txn_id, STATUS_DISMISSED)

    async def _set_status(
        self, txn_id: int, status: str, expense_id: Optional[int] = None
    ) -> None:
        def _update(db: Session) -> None:
            row = db.get(CapturedTransaction, txn_id)
            if row is None:
                return
            row.status = status
            if expense_id is not None:
                row.expense_id = expense_id
            db.commit()

        await run_db(_update)

    # ---- discovery checkpoint (high-water-mark) -----------------------------

    async def get_checkpoint(self, user_id: int) -> Optional[int]:
        def _get(db: Session) -> Optional[int]:
            row = db.scalar(
                select(CaptureState).where(CaptureState.user_id == user_id)
            )
            return row.gmail_last_checked_epoch if row else None

        return await run_db(_get)

    async def set_checkpoint(self, user_id: int, epoch: int) -> None:
        def _set(db: Session) -> None:
            row = db.scalar(
                select(CaptureState).where(CaptureState.user_id == user_id)
            )
            if row is None:
                row = CaptureState(
                    user_id=user_id,
                    gmail_last_checked_epoch=epoch,
                    created_at=utc_now(),
                )
                db.add(row)
            else:
                # Never move the checkpoint backwards.
                if row.gmail_last_checked_epoch is None or epoch > row.gmail_last_checked_epoch:
                    row.gmail_last_checked_epoch = epoch
            db.commit()

        await run_db(_set)
