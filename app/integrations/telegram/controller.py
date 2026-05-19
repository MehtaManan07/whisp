import logging
from fastapi import APIRouter, Header, HTTPException, status
from typing import Any, Dict, Optional

from app.core.dependencies import TelegramServiceDep
from app.core.exceptions import ValidationError
from app.integrations.telegram.dto import SendMessageDto
from app.integrations.telegram.schema import TelegramUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
async def handle_webhook(
    payload: Dict[str, Any],
    telegram_service: TelegramServiceDep,
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
) -> Dict[str, str]:
    """Receive an incoming Telegram update."""
    if not telegram_service.verify_secret(x_telegram_bot_api_secret_token):
        logger.warning("Rejected Telegram webhook: invalid secret token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid secret token",
        )

    try:
        update = TelegramUpdate.model_validate(payload)
        await telegram_service.handle_update(update)
    except Exception as e:
        logger.warning(f"Telegram webhook processing failed: {str(e)[:300]}")

    return {"status": "ok"}


@router.post("/send-text")
async def send_text(
    body: SendMessageDto,
    telegram_service: TelegramServiceDep,
) -> Dict[str, Any]:
    """Send a text message via Telegram (utility / manual use)."""
    if not body.chat_id or not body.chat_id.strip():
        raise ValidationError("chat_id is required")
    if not body.message or not body.message.strip():
        raise ValidationError("message is required")

    return await telegram_service.send_text(body.chat_id, body.message)


@router.get("/health")
async def health(telegram_service: TelegramServiceDep) -> Dict[str, Any]:
    """Verify the bot token is valid and the Telegram API reachable."""
    return await telegram_service.get_me()
