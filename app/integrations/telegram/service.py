import httpx
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from app.core.config import config
from app.core.exceptions import ValidationError, TelegramAPIError
from app.core.messaging import (
    HandleMessagePayload,
    IncomingContact,
    IncomingMessage,
    ProcessMessageResult,
)
from app.core.orchestrator import MessageOrchestrator
from app.integrations.telegram.schema import TelegramUpdate, TelegramMessage


logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self, orchestrator: MessageOrchestrator):
        self.bot_token = config.telegram_bot_token
        self.webhook_secret = config.telegram_webhook_secret
        self.allowed_user_id = config.telegram_allowed_user_id
        self.orchestrator = orchestrator
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"

    # -------------------------------------------------------------------------
    # Inbound
    # -------------------------------------------------------------------------

    def verify_secret(self, header_value: Optional[str]) -> bool:
        """Verify the X-Telegram-Bot-Api-Secret-Token header set during webhook registration."""
        if not self.webhook_secret:
            return True
        return header_value == self.webhook_secret

    async def handle_update(self, update: TelegramUpdate) -> None:
        """Process an incoming Telegram update."""
        message = update.message or update.edited_message
        if not message or not message.from_:
            return

        sender_id = message.from_.id

        if self.allowed_user_id and sender_id != self.allowed_user_id:
            logger.warning(
                f"Ignoring message from non-allowlisted Telegram user {sender_id} "
                f"(@{message.from_.username})"
            )
            return

        if not message.text:
            return

        if self._is_stale(message):
            return

        start_time = time.time()

        payload = HandleMessagePayload(
            sender_id=str(sender_id),
            contact=IncomingContact(
                external_id=str(sender_id),
                name=message.from_.display_name or None,
            ),
            message=IncomingMessage(
                id=str(message.message_id),
                text=message.text,
                reply_to_id=(
                    str(message.reply_to_message.message_id)
                    if message.reply_to_message
                    else None
                ),
            ),
        )

        response = await self.orchestrator.handle_new_message(payload=payload)

        await self._send_bot_responses(response, chat_id=message.chat.id)

        latency_ms = (time.time() - start_time) * 1000
        display = message.text if len(message.text) <= 50 else message.text[:50] + "..."
        logger.debug(
            f"Telegram E2E Latency: {latency_ms:.2f}ms | User: {sender_id} | Message: '{display}'"
        )

    def _is_stale(self, message: TelegramMessage) -> bool:
        try:
            sent_at = datetime.fromtimestamp(message.date)
            return datetime.now() - sent_at > timedelta(minutes=2)
        except Exception:
            return False

    async def _send_bot_responses(
        self, response: Optional[ProcessMessageResult], chat_id: int
    ) -> None:
        if not response or not response.messages:
            return

        for idx, msg in enumerate(response.messages, 1):
            try:
                await self.send_text(str(chat_id), msg)
            except Exception as e:
                logger.error(
                    f"Failed to send message {idx}/{len(response.messages)} "
                    f"to chat {chat_id}: {str(e)}"
                )

    # -------------------------------------------------------------------------
    # Outbound
    # -------------------------------------------------------------------------

    async def send_text(
        self, to: str, text: str, disable_web_page_preview: bool = False
    ) -> Dict[str, Any]:
        """Send a text message via Telegram Bot API."""
        if not to or not str(to).strip():
            raise ValidationError("Recipient chat ID is required")
        if not text or not text.strip():
            raise ValidationError("Message text is required")

        url = f"{self.api_base}/sendMessage"
        payload = {
            "chat_id": to,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": disable_web_page_preview,
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(url, json=payload)
                data = response.json()

                if not response.is_success or not data.get("ok"):
                    description = data.get("description", "Unknown error")
                    logger.error(f"Telegram sendMessage failed: {data}")

                    if "can't parse entities" in description.lower() or "parse" in description.lower():
                        payload.pop("parse_mode", None)
                        response = await client.post(url, json=payload)
                        data = response.json()
                        if response.is_success and data.get("ok"):
                            return data
                        description = data.get("description", description)

                    raise TelegramAPIError(f"Failed to send message: {description}")

                return data

        except httpx.RequestError as e:
            logger.error(f"Network error sending Telegram message: {str(e)}")
            raise TelegramAPIError(f"Network error: {str(e)}")
        except TelegramAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message: {e}")
            raise TelegramAPIError(f"Unexpected error: {str(e)}")

    # -------------------------------------------------------------------------
    # Admin helpers (used by setup scripts and health checks)
    # -------------------------------------------------------------------------

    async def get_me(self) -> Dict[str, Any]:
        """Call getMe to verify the bot token is valid."""
        url = f"{self.api_base}/getMe"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            data = response.json()
            if not data.get("ok"):
                raise TelegramAPIError(f"getMe failed: {data.get('description')}")
            return data["result"]

    async def set_webhook(self, url: str) -> Dict[str, Any]:
        """Register the webhook URL with Telegram. Pass the public HTTPS URL of /telegram/webhook."""
        endpoint = f"{self.api_base}/setWebhook"
        payload = {
            "url": url,
            "secret_token": self.webhook_secret,
            "allowed_updates": ["message", "edited_message"],
            "drop_pending_updates": True,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(endpoint, json=payload)
            data = response.json()
            if not data.get("ok"):
                raise TelegramAPIError(f"setWebhook failed: {data.get('description')}")
            return data
