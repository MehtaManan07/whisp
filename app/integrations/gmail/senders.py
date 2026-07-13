"""
Transaction-email sender allowlist + Gmail query builder.

The capture pipeline is intentionally LLM-first: we only use this allowlist to
*pre-filter* Gmail down to likely transaction alerts (the cheap, precise step),
then hand the matching emails to the LLM extractor. When cards change, edit only
this list — nothing else in the pipeline needs to move.
"""

from dataclasses import dataclass, field
from typing import Optional, Sequence


@dataclass(frozen=True)
class TransactionSender:
    """One bank/card transaction-alert sender."""

    bank: str
    from_email: str
    # Optional subject keywords to tighten the Gmail pre-filter for this sender.
    # Leave empty to match every email from the sender (LLM still filters noise).
    subject_keywords: Sequence[str] = field(default_factory=tuple)


# Edit this list as cards change. Keep from_email lowercased.
TRANSACTION_SENDERS: list[TransactionSender] = [
    TransactionSender(
        bank="HDFC Bank",
        from_email="alerts@hdfcbank.bank.in",
    ),
    TransactionSender(
        bank="ICICI Bank Credit Card",
        from_email="credit_cards@icici.bank.in",
    ),
]


def _sender_clause(sender: TransactionSender) -> str:
    clause = f"from:{sender.from_email}"
    if sender.subject_keywords:
        subject = " OR ".join(f'subject:{kw}' for kw in sender.subject_keywords)
        clause = f"({clause} ({subject}))"
    return clause


def build_transaction_query(
    senders: Optional[Sequence[TransactionSender]] = None,
    newer_than_days: Optional[int] = 1,
    after_epoch: Optional[int] = None,
) -> str:
    """
    Build a Gmail search query that matches transaction alerts from the given
    senders (from:/subject: pre-filter).

    Scope precedence: if ``after_epoch`` (epoch seconds) is given, use a
    high-water-mark ``after:<epoch>`` (survives downtime with no gap); otherwise
    fall back to ``newer_than:<days>d``.

    Example:
        (from:alerts@hdfcbank.bank.in OR from:credit_cards@icici.bank.in) after:1718900000
    """
    senders = list(senders if senders is not None else TRANSACTION_SENDERS)
    if not senders:
        return ""

    clauses = [_sender_clause(s) for s in senders]
    query = " OR ".join(clauses)
    if len(clauses) > 1:
        query = f"({query})"

    if after_epoch and after_epoch > 0:
        query = f"{query} after:{after_epoch}"
    elif newer_than_days and newer_than_days > 0:
        query = f"{query} newer_than:{newer_than_days}d"

    return query


def bank_for_sender(
    from_email: str,
    senders: Optional[Sequence[TransactionSender]] = None,
) -> Optional[str]:
    """Resolve a sender email address back to its bank/card label."""
    senders = senders if senders is not None else TRANSACTION_SENDERS
    target = (from_email or "").lower().strip()
    for sender in senders:
        if sender.from_email.lower() == target:
            return sender.bank
    return None
