import logging
from fastapi import APIRouter, Depends, Query, Body
from typing import Dict, Any
from app.core.dependencies import (
    DatabaseDep,
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
    logger.info("Webhook verification request received")
    return await whatsapp_service.verify_webhook(mode, token, challenge)


@router.post("/webhook")
async def handle_webhook(
    payload: WebhookPayload,
    db: DatabaseDep,
    whatsapp_service: WhatsAppServiceDep,
) -> Dict[str, str]:
    """Handle incoming WhatsApp webhook"""
    logger.info("Webhook payload received")
    await whatsapp_service.handle_webhook(payload, db)
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
    
    logger.info(f"Sending message to {body.recipient}")
    result = await whatsapp_service.send_text(body.recipient, body.message, True)
    return result


# Example endpoint showing how to use IntentClassifier directly
@router.post("/classify-intent")
async def classify_intent(
    intent_classifier: IntentClassifierDep,
    message: str = Body(embed=True),
) -> Dict[str, str]:
    """Classify intent of a message (for testing)"""
    if not message or not message.strip():
        raise ValidationError("Message is required")
    
    logger.info(f"Classifying intent for message: {message}")
    intent = await intent_classifier.classify(message)
    return {"message": message, "intent": intent.value}
