import httpx
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import config
from app.core.exceptions import WhatsAppAPIError, ValidationError
from app.integrations.whatsapp.schema import (
    WebhookPayload,
    ProcessMessageResult,
    HandleMessagePayload,
)

from app.core.orchestrator import MessageOrchestrator


logger = logging.getLogger(__name__)


class WhatsAppService:
    def __init__(self, orchestrator: MessageOrchestrator):
        self.webhook_verify_token = config.wa_verify_token
        self.access_token = config.wa_access_token
        self.phone_number_id = config.wa_phone_number_id
        self.orchestrator = orchestrator

    async def verify_webhook(self, mode: str, token: str, challenge: str) -> int:
        """Verify webhook subscription"""
        if mode == "subscribe" and token == self.webhook_verify_token:
            logger.info("Webhook verified successfully!")
            return int(challenge)

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Verification failed",
        )

    async def handle_webhook(self, payload: WebhookPayload, db: AsyncSession) -> None:
        """Process incoming WhatsApp webhook payload"""
        change = payload.entry[0].changes[0] if payload.entry else None

        if not change or change.field != "messages":
            return

        messages = change.value.messages or []
        contacts = change.value.contacts or []
        contact = contacts[0] if contacts else None

        if not messages or not contact:
            return

        for message in messages:
            from_number = message.from_
            message_type = message.type
            context = message.context
            timestamp = message.timestamp

            # Ignore unsupported or system-level messages
            if not from_number or message_type == "image":
                continue

            # Freshness check
            if timestamp:
                message_time = datetime.fromtimestamp(int(timestamp))
                now = datetime.now()
                age = now - message_time

                if age > timedelta(
                    minutes=0.25
                ):  # Ignore messages older than 0.5 minute
                    logger.info(f"Ignoring old message from {from_number} (age: {age})")
                    continue

            response = await self.orchestrator.handle_new_message(
                payload=HandleMessagePayload(
                    **{"from": from_number},
                    contact=contact,
                    message=message,
                ),
                db=db,
            )

            await self._send_bot_responses(response, from_number)

    async def send_text(
        self, to: str, text: str, preview_url: bool = True
    ) -> Dict[str, Any]:
        """Send text message via WhatsApp API"""
        if not to or not to.strip():
            raise ValidationError("Recipient phone number is required")
        
        if not text or not text.strip():
            raise ValidationError("Message text is required")
        
        try:
            url = f"https://graph.facebook.com/v23.0/{self.phone_number_id}/messages"

            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {
                    "preview_url": preview_url,
                    "body": text,
                },
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.access_token}",
                    },
                )

                if not response.is_success:
                    error_data = response.json()
                    error_message = error_data.get('error', {}).get('message', 'Unknown error')
                    logger.error(f"Failed to send WhatsApp message: {error_data}")
                    raise WhatsAppAPIError(f"Failed to send message: {error_message}")

                result = response.json()
                logger.info(f"WhatsApp message sent successfully to {to}")
                return result

        except httpx.RequestError as e:
            logger.error(f"Network error sending WhatsApp message: {str(e)}")
            raise WhatsAppAPIError(f"Network error: {str(e)}")
        except WhatsAppAPIError:
            raise
        except Exception as error:
            logger.error(f"Unexpected error sending WhatsApp message: {error}")
            raise WhatsAppAPIError(f"Unexpected error: {str(error)}")


    async def _send_bot_responses(
        self, response: Optional[ProcessMessageResult], recipient: str
    ) -> None:
        """Send bot responses to user"""
        if not response or not response.messages:
            return

        # Send messages for both success and error responses
        for msg in response.messages:
            try:
                await self.send_text(recipient, msg)
            except Exception as e:
                logger.error(f"Failed to send error message to user {recipient}: {str(e)}")
                # Don't re-raise here to avoid infinite error loops


