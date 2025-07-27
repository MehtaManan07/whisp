import httpx
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status

from app.infra.config import config
from app.communication.whatsapp.schema import (
    WebhookPayload,
    ProcessMessageResult,
    HandleMessagePayload,
)


logger = logging.getLogger(__name__)


class WhatsAppService:
    def __init__(self):
        self.webhook_verify_token = config.wa_verify_token
        self.access_token = config.wa_access_token
        self.phone_number_id = config.wa_phone_number_id

    async def verify_webhook(self, mode: str, token: str, challenge: str) -> int:
        """Verify webhook subscription"""
        if mode == "subscribe" and token == self.webhook_verify_token:
            logger.info("Webhook verified successfully!")
            return int(challenge)

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Verification failed",
        )

    async def handle_webhook(self, payload: WebhookPayload) -> None:
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
                print(f"Processing message from {from_number} at {timestamp}")
                message_time = datetime.fromtimestamp(int(timestamp))
                now = datetime.now()
                age = now - message_time

                if age > timedelta(minutes=1):  # Ignore messages older than 1 minute
                    continue

            is_reply = bool(context)

            if is_reply:
                response = await self._handle_reply(
                    HandleMessagePayload(
                        **{"from": from_number},
                        contact=contact,
                        message=message,
                    )
                )
            else:
                response = await self._handle_new_message(
                    HandleMessagePayload(
                        **{"from": from_number},
                        contact=contact,
                        message=message,
                    )
                )

            await self._send_bot_responses(response, from_number)

    async def send_text(
        self, to: str, text: str, preview_url: bool = True
    ) -> Dict[str, Any]:
        """Send text message via WhatsApp API"""
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
                    logger.error(f"Failed to send WhatsApp message: {error_data}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to send message: {error_data.get('error', {}).get('message', 'Unknown error')}",
                    )

                result = response.json()
                logger.info(f"WhatsApp message sent successfully to {to}")
                return result

        except Exception as error:
            logger.error(f"Error sending WhatsApp message: {error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send WhatsApp message",
            )

    async def _handle_reply(
        self, data: HandleMessagePayload
    ) -> Optional[ProcessMessageResult]:
        """Handle reply messages - implement your logic here"""
        # TODO: Implement message handler service
        logger.info(f"Handling reply from {data.from_}")
        return ProcessMessageResult(status="success", messages=["Reply received!"])

    async def _handle_new_message(
        self, data: HandleMessagePayload
    ) -> Optional[ProcessMessageResult]:
        """Handle new messages - implement your logic here"""
        # TODO: Implement message handler service
        logger.info(f"Handling new message from {data.from_}")
        return ProcessMessageResult(status="success", messages=["Message received!"])

    async def _send_bot_responses(
        self, response: Optional[ProcessMessageResult], recipient: str
    ) -> None:
        """Send bot responses to user"""
        if not response or response.status != "success" or not response.messages:
            return

        for msg in response.messages:
            await self.send_text(recipient, msg)


# Global service instance
whatsapp_service = WhatsAppService()
