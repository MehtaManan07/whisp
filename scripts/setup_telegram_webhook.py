"""
Register the Telegram webhook with Bot API.

Run after deploy (or after changing APP_BASE_URL) to point Telegram at this server.

Usage:
    python -m scripts.setup_telegram_webhook
    python -m scripts.setup_telegram_webhook --url https://example.com
"""

import argparse
import asyncio
import sys

from app.core.config import config
from app.integrations.telegram.service import TelegramService


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default=None,
        help="Override the public base URL. Defaults to APP_BASE_URL from .env.",
    )
    args = parser.parse_args()

    if not config.telegram_bot_token:
        print("ERROR: TELEGRAM_BOT_TOKEN is not set in .env", file=sys.stderr)
        return 1

    if not config.telegram_webhook_secret:
        print(
            "ERROR: TELEGRAM_WEBHOOK_SECRET is not set in .env. "
            "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'",
            file=sys.stderr,
        )
        return 1

    base_url = (args.url or config.app_base_url).rstrip("/")
    if not base_url:
        print("ERROR: pass --url or set APP_BASE_URL in .env", file=sys.stderr)
        return 1

    webhook_url = f"{base_url}/telegram/webhook"

    service = TelegramService(orchestrator=None)  # type: ignore[arg-type]

    print(f"Verifying bot token...")
    me = await service.get_me()
    print(f"  Bot: @{me.get('username')} (id={me.get('id')}, name={me.get('first_name')})")

    print(f"Registering webhook: {webhook_url}")
    result = await service.set_webhook(webhook_url)
    print(f"  {result.get('description', 'ok')}")

    if config.telegram_allowed_user_id:
        print(f"Allowlist: only Telegram user {config.telegram_allowed_user_id} will be accepted")
    else:
        print("WARNING: no TELEGRAM_ALLOWED_USER_ID set — anyone who DMs the bot will be auto-registered")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
