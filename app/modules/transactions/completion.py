"""
Reply-driven completion of a captured transaction.

When the user replies (reply-threaded) to a capture prompt bubble, this correlates
the reply to the pending CapturedTransaction and logs the expense from the user's
description — running it through the normal categorization, with the email amount
pre-bound (overridden only if the user states an amount). ``skip`` dismisses it.
"""

import logging
from typing import Optional

from app.core.messaging import HandleMessagePayload, ProcessMessageResult
from app.modules.expenses.dto import CreateExpenseModel
from app.modules.transactions.dto import CapturedTransactionData
from app.modules.transactions.models import STATUS_AWAITING
from app.modules.users.models import User

logger = logging.getLogger(__name__)

# Replies that dismiss a capture instead of logging it.
SKIP_WORDS = {"skip", "ignore", "not mine", "dismiss", "cancel", "no"}


def _confirmation(amount: float, vendor: Optional[str], category: Optional[str]) -> str:
    who = f" at {vendor}" if vendor else ""
    cat = f" · {category}" if category else ""
    return f"✅ Logged ₹{amount:,.2f}{who}{cat}"


async def try_complete_capture(
    payload: HandleMessagePayload, user: User
) -> Optional[ProcessMessageResult]:
    """
    If this message is a reply to a pending capture prompt, complete it and return
    a result. Otherwise return None so normal free-text handling proceeds.
    """
    reply_to_id = payload.message.reply_to_id
    if not reply_to_id:
        return None

    from app.core.dependencies import (
        get_category_classifier,
        get_expense_service,
        get_llm_service,
        get_transactions_service,
    )

    txns = get_transactions_service()
    record: Optional[CapturedTransactionData] = await txns.get_by_telegram_message_id(
        str(reply_to_id)
    )
    if record is None:
        # Reply wasn't to a capture bubble — not ours.
        return None

    if record.status != STATUS_AWAITING:
        return ProcessMessageResult(
            status="success",
            messages=["That charge is already handled. 👍"],
        )

    text = (payload.message.text or "").strip()
    if text.lower() in SKIP_WORDS:
        await txns.mark_dismissed(record.id)
        return ProcessMessageResult(
            status="success",
            messages=["❌ Skipped — not logged."],
        )

    if record.amount is None:
        await txns.mark_dismissed(record.id)
        return ProcessMessageResult(
            status="success",
            messages=["⚠️ That charge had no amount — skipped."],
        )

    llm = get_llm_service()
    classifier = get_category_classifier()
    expenses = get_expense_service()

    from app.intelligence.extraction.txn_extractor import extract_expense_from_reply

    parsed = await extract_expense_from_reply(text, record.amount, llm)

    # Amount rule: user's stated amount wins, else the email amount.
    amount = parsed.amount if (parsed.amount and parsed.amount > 0) else record.amount
    # Date rule: user's stated time wins, else the email transaction time.
    timestamp = parsed.occurred_at or record.transaction_date
    vendor = parsed.vendor
    note = parsed.note

    # Categorize from the user's words (the accurate signal).
    category_name = subcategory_name = None
    try:
        dto = CreateExpenseModel(
            user_id=user.id, amount=amount, vendor=vendor, note=note
        )
        result = await classifier.classify(
            original_message=text, dto_instance=dto, user_id=user.id
        )
        category_name = result.get("category")
        subcategory_name = result.get("subcategory")
    except Exception as e:
        logger.warning("Capture completion classification failed: %s", e)

    user_timezone = user.timezone or "UTC"
    try:
        await expenses.create_expense(
            CreateExpenseModel(
                user_id=user.id,
                amount=amount,
                vendor=vendor,
                category_name=category_name,
                subcategory_name=subcategory_name,
                note=note,
                source_message_id=record.gmail_message_id,
                timestamp=timestamp,
            ),
            user_timezone=user_timezone,
        )
    except Exception as e:
        logger.error("Failed to log expense from capture %s: %s", record.id, e)
        return ProcessMessageResult(
            status="error",
            messages=["⚠️ Something went wrong logging that. Please try again."],
        )

    await txns.mark_logged(record.id)
    display_cat = " › ".join(b for b in [category_name, subcategory_name] if b) or None
    return ProcessMessageResult(
        status="success",
        messages=[_confirmation(amount, vendor, display_cat)],
    )
