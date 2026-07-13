import json
import logging
from datetime import datetime, timezone
from typing import Optional

import dateparser
from pydantic import BaseModel, Field

from app.integrations.gmail.dto import EmailDTO
from app.integrations.llm.service import LLMService
from app.intelligence.extraction.txn_prompts import (
    build_describe_expense_prompt,
    build_transaction_email_prompt,
)

logger = logging.getLogger(__name__)


class ExtractedTransaction(BaseModel):
    """Structured result of parsing a transaction-alert email."""

    is_transaction: bool = False
    direction: Optional[str] = None  # "debit" | "credit"
    amount: Optional[float] = None
    currency: Optional[str] = Field(default="INR")
    vendor: Optional[str] = None
    transaction_datetime: Optional[datetime] = None
    card_last4: Optional[str] = None
    reference: Optional[str] = None

    @property
    def is_loggable_expense(self) -> bool:
        """Only completed debits with a positive amount become expenses."""
        return (
            self.is_transaction
            and self.direction == "debit"
            and self.amount is not None
            and self.amount > 0
        )


def _coerce_datetime(value, fallback: Optional[datetime]) -> Optional[datetime]:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        dt = dateparser.parse(value)
    else:
        dt = None

    if dt is None:
        dt = fallback
    if dt is None:
        return None

    # Normalize to timezone-aware UTC (timestamps are stored in UTC).
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def extract_transaction_from_email(
    email: EmailDTO,
    bank: str,
    llm_service: LLMService,
) -> Optional[ExtractedTransaction]:
    """
    Parse a single transaction-alert email into an ExtractedTransaction via LLM.
    Returns None on hard failure (caller should skip/ignore the email).
    """
    received_at = (
        email.date.isoformat() if email.date else datetime.now().isoformat()
    )
    prompt = build_transaction_email_prompt(
        bank=bank,
        subject=email.subject,
        body=email.body or email.snippet,
        received_at=received_at,
    )

    try:
        response = await llm_service.complete_with_groq(
            prompt=prompt,
            temperature=0,
            call_stack="txn_extraction",
        )
        parsed = json.loads(response.content)
    except json.JSONDecodeError as e:
        logger.warning("Txn extractor returned invalid JSON for %s: %s", email.id, e)
        return None
    except Exception as e:
        logger.error("Txn extraction failed for %s: %s", email.id, e)
        return None

    parsed["transaction_datetime"] = _coerce_datetime(
        parsed.get("transaction_datetime"), email.date
    )
    if parsed.get("vendor"):
        parsed["vendor"] = str(parsed["vendor"]).strip() or None
    if parsed.get("direction"):
        parsed["direction"] = str(parsed["direction"]).strip().lower()

    try:
        return ExtractedTransaction(**parsed)
    except Exception as e:
        logger.warning("Could not build ExtractedTransaction for %s: %s", email.id, e)
        return None


class ReplyExpense(BaseModel):
    """What the user told us when describing an email-captured charge."""

    vendor: Optional[str] = None
    amount: Optional[float] = None
    note: Optional[str] = None
    occurred_at: Optional[datetime] = None


async def extract_expense_from_reply(
    reply_text: str,
    email_amount: float,
    llm_service: LLMService,
) -> ReplyExpense:
    """
    Parse a user's free-text description of a captured charge. Amount is optional
    (defaults to the email amount upstream); only an explicitly stated amount overrides.
    """
    prompt = build_describe_expense_prompt(reply_text, email_amount)
    try:
        response = await llm_service.complete_with_groq(
            prompt=prompt,
            temperature=0,
            call_stack="reply_expense_extraction",
        )
        parsed = json.loads(response.content)
    except Exception as e:
        logger.warning("Reply expense extraction failed: %s", e)
        # Fall back to using the raw reply as the vendor/note.
        return ReplyExpense(vendor=reply_text.strip() or None)

    parsed["occurred_at"] = _coerce_datetime(parsed.get("occurred_at"), None)
    if parsed.get("vendor"):
        parsed["vendor"] = str(parsed["vendor"]).strip() or None
    try:
        return ReplyExpense(**parsed)
    except Exception as e:
        logger.warning("Could not build ReplyExpense: %s", e)
        return ReplyExpense(vendor=reply_text.strip() or None)
