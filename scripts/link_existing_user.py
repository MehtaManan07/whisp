"""
Link an existing user row to a Telegram ID so their expense/reminder history
stays intact after the WhatsApp → Telegram migration.

Run once on the deployed environment after applying the alembic migration that
adds the telegram_id column.

Usage:
    python -m scripts.link_existing_user <telegram_id>
    python -m scripts.link_existing_user <telegram_id> --user-id <user_id>
"""

import argparse
import sys

from sqlalchemy import select, update

from app.core.db.engine import SessionLocal
from app.modules.users.models import User
# Import all models so SQLAlchemy can resolve string-referenced relationships.
from app.modules.expenses.models import Expense  # noqa: F401
from app.modules.reminders.models import Reminder  # noqa: F401
from app.modules.categories.models import Category  # noqa: F401
from app.modules.budgets.models import Budget  # noqa: F401


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("telegram_id", help="Your Telegram user ID")
    parser.add_argument(
        "--user-id",
        type=int,
        default=None,
        help="Specific user.id to link. If omitted, links the earliest-created user.",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.user_id:
            user = db.execute(select(User).where(User.id == args.user_id)).scalar_one_or_none()
            if not user:
                print(f"ERROR: no user with id={args.user_id}", file=sys.stderr)
                return 1
        else:
            user = db.execute(
                select(User).order_by(User.created_at.asc()).limit(1)
            ).scalar_one_or_none()
            if not user:
                print("No existing users in DB — nothing to link. First message will auto-create.")
                return 0

        existing = db.execute(
            select(User).where(User.telegram_id == args.telegram_id)
        ).scalar_one_or_none()
        if existing and existing.id != user.id:
            print(
                f"ERROR: telegram_id {args.telegram_id} is already linked to user {existing.id}",
                file=sys.stderr,
            )
            return 1

        if user.telegram_id == args.telegram_id:
            print(f"User {user.id} ({user.name}) is already linked to telegram_id {args.telegram_id}")
            return 0

        db.execute(
            update(User).where(User.id == user.id).values(telegram_id=args.telegram_id)
        )
        db.commit()
        print(f"Linked user {user.id} ({user.name}) → telegram_id={args.telegram_id}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
