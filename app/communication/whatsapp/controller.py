import logging
from fastapi import APIRouter, Depends, Query, Body
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.communication.whatsapp.dto import SendMessageDto
from app.communication.whatsapp.schema import WebhookPayload
from app.communication.whatsapp.service import whatsapp_service
from app.infra.db.engine import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.get("/webhook")
async def verify_webhook(
    mode: str = Query(alias="hub.mode"),
    token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge"),
) -> int:
    """Verify WhatsApp webhook subscription"""
    logger.info("Webhook verification request received")
    return await whatsapp_service.verify_webhook(mode, token, challenge)


@router.post("/webhook")
async def handle_webhook(
    payload: WebhookPayload, db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Handle incoming WhatsApp webhook"""
    logger.info("Webhook payload received")
    await whatsapp_service.handle_webhook(payload, db)
    return {"status": "ok"}


@router.post("/send-text")
async def send_text(body: SendMessageDto) -> Dict[str, Any]:
    """Send text message via WhatsApp"""
    logger.info(f"Sending message to {body.recipient}")
    result = await whatsapp_service.send_text(body.recipient, body.message, True)
    return result
