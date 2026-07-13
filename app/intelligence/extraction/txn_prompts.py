from datetime import datetime


def build_transaction_email_prompt(
    bank: str,
    subject: str,
    body: str,
    received_at: str,
) -> str:
    """
    Prompt the LLM to turn a bank/card transaction-alert email into a single
    structured JSON object. Robust to per-bank formatting (this replaces the old
    per-bank regex parser).
    """
    # Keep the body bounded — alerts are short, and this caps token usage.
    body = (body or "").strip()
    if len(body) > 4000:
        body = body[:4000]

    return f"""
You are a precise parser of bank and credit-card transaction-alert emails.
Extract the transaction into a single JSON object. Return ONLY the JSON object,
no explanation, no markdown.

### Output schema (all keys required, use null when unknown):
{{
  "is_transaction": boolean,   // true only if this email reports an actual money movement on a card/account
  "direction": "debit" | "credit" | null,  // "debit" = money spent/withdrawn; "credit" = money received/refunded
  "amount": number | null,     // numeric amount only, no currency symbol or commas
  "currency": string | null,   // ISO-ish code, e.g. "INR"
  "vendor": string | null,     // merchant / payee name, cleaned (e.g. "SWIGGY", "AMAZON"). null if not present
  "transaction_datetime": string | null,  // ISO 8601, e.g. "2026-06-20T19:34:00". Use the email's transaction time; if only a date is given, use T00:00:00
  "card_last4": string | null, // last 4 digits of the card/account if present
  "reference": string | null   // bank reference / UPI ref number if present
}}

### Rules:
- Set is_transaction=false for OTPs, statements, promotions, reminders, failed/declined alerts, or anything that is not a completed transaction. When false, other fields may be null.
- Only money LEAVING the account is a "debit" (spent). Refunds, cashbacks, salary, and received payments are "credit".
- Do NOT fabricate a vendor. If the email does not name a merchant, set vendor to null.
- amount must be a plain number (e.g. 1234.50), never a string.
- For relative or partial dates, resolve against the email received time below.

### Context:
- Bank/Card: {bank}
- Email received at: {received_at}
- Today: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}

### Email subject:
{subject}

### Email body:
{body}

### Return ONLY the JSON object:
""".strip()


def build_describe_expense_prompt(reply_text: str, email_amount: float) -> str:
    """
    Parse the user's free-text reply describing an email-captured charge.

    The amount is already known from the bank email (``email_amount``); the user
    only needs to say what it was. They MAY override the amount by stating a new one.
    """
    return f"""
You are extracting a single expense from a short user message. The user is
describing a card charge we already detected. The known charge amount is
{email_amount}, but the user may state a different amount to override it.

### Output schema (return ONLY this JSON object):
{{
  "vendor": string | null,     // merchant/place the user named, cleaned (e.g. "swiggy"). null if none
  "amount": number | null,     // ONLY if the user explicitly stated an amount; else null
  "note": string | null,       // any extra detail worth keeping; else null
  "occurred_at": string | null // ISO 8601 ONLY if the user stated a time/date; else null
}}

### Rules:
- Do NOT invent a vendor. If the user gave only a category word (e.g. "food"), set vendor to null.
- Set amount only when the user clearly states a number as the price (e.g. "swiggy 500", "it was 320"). Otherwise null — we will use the known charge amount.
- Today is {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}.
- Return a plain number for amount (no symbols/commas), never a string.

### User message:
{reply_text}

### Return ONLY the JSON object:
""".strip()
