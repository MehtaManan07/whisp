"""
Run bank transaction scan once and print pending prompts.

Usage:
    python -m scripts.run_bank_transaction_check
    python -m scripts.run_bank_transaction_check --max-results 100
"""

import argparse
import asyncio
from dotenv import load_dotenv

load_dotenv()


async def _run(max_results: int) -> None:
    from app.core.config import config
    from app.core.dependencies import get_bank_transaction_service

    service = get_bank_transaction_service()

    print("Running bank transaction email processing...")
    result = await service.process_emails(max_results=max_results)

    print("\n=== Processing Result ===")
    print(f"Processed: {result.processed_count}")
    print(f"WhatsApp prompts sent: {result.sent_count}")
    print(f"Errors: {len(result.errors)}")
    if result.errors:
        print("\nError details:")
        for err in result.errors:
            print(f"- {err}")

    wa_id = config.bank_transactions_whatsapp_number
    if not wa_id:
        print("\nBANK_TRANSACTIONS_WHATSAPP_NUMBER is not configured.")
        return

    pending_items = await service.get_all_pending_confirmations(wa_id)
    print("\n=== Pending Expense Prompts ===")
    print(f"WhatsApp user: {wa_id}")
    print(f"Pending count: {len(pending_items)}")

    for idx, item in enumerate(pending_items, start=1):
        amount = item.transaction_data.amount
        bank = item.transaction_data.bank
        prompt_id = item.prompt_message_id or "N/A"
        print(
            f"{idx}. ₹{amount:,.2f} | bank={bank} | gmail_message_id={item.gmail_message_id} | prompt_message_id={prompt_id}"
        )

    print("\nNext step:")
    print("- Reply on WhatsApp to the exact prompt message with expense description.")
    print("- Example reply: groceries / rapido / sent money to friend")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run one-shot bank transaction email processing"
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=50,
        help="Max Gmail emails to fetch in one run (default: 50)",
    )
    args = parser.parse_args()
    asyncio.run(_run(max_results=args.max_results))


if __name__ == "__main__":
    main()
