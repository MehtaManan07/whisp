import logging
from fastapi import APIRouter, Depends, Query, Body
from typing import Dict, Any
from app.core.dependencies import (
    WhatsAppServiceDep,
    IntentClassifierDep,
)
from app.core.exceptions import ValidationError, WhatsAppAPIError
from app.integrations.whatsapp.dto import SendMessageDto
from app.integrations.whatsapp.schema import WebhookPayload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.get("/webhook")
async def verify_webhook(
    whatsapp_service: WhatsAppServiceDep,
    mode: str = Query(alias="hub.mode"),
    token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge"),
) -> int:
    """Verify WhatsApp webhook subscription"""
    return await whatsapp_service.verify_webhook(mode, token, challenge)


@router.post("/webhook")
async def handle_webhook(
    payload: Dict[str, Any],
    whatsapp_service: WhatsAppServiceDep,
) -> Dict[str, str]:
    """Handle incoming WhatsApp webhook"""
    try:
        validated_payload = WebhookPayload(**payload)
        await whatsapp_service.handle_webhook(validated_payload)
    except Exception as e:
        logger.warning(f"Webhook validation/processing failed: {str(e)[:200]}")

    return {"status": "ok"}


@router.post("/send-text")
async def send_text(
    body: SendMessageDto,
    whatsapp_service: WhatsAppServiceDep,
) -> Dict[str, Any]:
    """Send text message via WhatsApp"""
    if not body.recipient or not body.recipient.strip():
        raise ValidationError("Recipient is required")

    if not body.message or not body.message.strip():
        raise ValidationError("Message content is required")

    result = await whatsapp_service.send_text(body.recipient, body.message, True)
    return result


@router.post("/classify-intent")
async def classify_intent(
    intent_classifier: IntentClassifierDep,
    message: str = Body(embed=True),
) -> Dict[str, str]:
    """Classify intent of a message (for testing)"""
    if not message or not message.strip():
        raise ValidationError("Message is required")

    intent = await intent_classifier.classify(message)
    return {"message": message, "intent": intent.value}
