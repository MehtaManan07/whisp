import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.communication.whatsapp.schema import HandleMessagePayload, ProcessMessageResult
from app.modules.users.dto import CreateUserDto
from app.modules.users.service import users_service
import app.utils.constants.whatsapp_responses as message_constants

logger = logging.getLogger(__name__)


class MessageHandlerService:
    def __init__(self):
        self.logger = logger

    async def handle_new_message(
        self, payload: HandleMessagePayload, db: AsyncSession
    ) -> Optional[ProcessMessageResult]:
        """Handle new incoming messages"""
        self.logger.info(f"Handling new message: {payload}")

        await users_service.find_or_create(
            db=db,
            user_data=CreateUserDto(
                wa_id=payload.contact.wa_id,
                phone_number=payload.from_,
                name=payload.contact.profile.get("name", ""),
            ),
        )

        text = (
            payload.message.text.body.strip().lower() if payload.message.text else None
        )
        if not text:
            return None

        # Check if it's a command (starts with /)
        if text.startswith("/"):
            return await self.handle_command(payload, db)
        else:
            return await self.handle_free_text(payload, db)

    async def handle_command(
        self, payload: HandleMessagePayload, db: AsyncSession
    ) -> Optional[ProcessMessageResult]:
        """Handle command messages (starting with /)"""
        text = (
            payload.message.text.body.strip().lower() if payload.message.text else None
        )
        if not text:
            return None

        match text:
            case "/help":
                return await self.handle_help_command(payload, db)
            case _:
                # Unknown command
                return ProcessMessageResult(
                    messages=[
                        'Unknown command. Try "/help" to see available commands.'
                    ],
                    status="success",
                )

    async def handle_free_text(
        self, payload: HandleMessagePayload, db: AsyncSession
    ) -> Optional[ProcessMessageResult]:
        """Handle free text messages (not commands)"""
        """
        handle_free_text() 
      → classify intent (expense logging / reflection / chat)
      → if expense → parse it → log to DB → return friendly reply
      → if reflection → store it → generate LLM summary
      → else → fallback to LLM (generic chat)

        """
        # Default fallback for free text
        return ProcessMessageResult(
            messages=['Hmm, I didn\'t get that. Try "log" or "wakeup" to get started.'],
            status="success",
        )

    async def handle_help_command(
        self, payload: HandleMessagePayload, db: AsyncSession
    ) -> ProcessMessageResult:
        """Handle hemp command"""

        message = message_constants.HELP_MESSAGES.help(
            name=payload.contact.profile.get("name", "buddy")
        )

        return ProcessMessageResult(messages=[message], status="success")

    async def handle_reply(
        self, payload: HandleMessagePayload, db: AsyncSession
    ) -> Optional[ProcessMessageResult]:
        """Handle reply messages"""
        text = payload.message.text.body if payload.message.text else None
        replied_to_message_id = (
            payload.message.context.id if payload.message.context else None
        )

        if not text:
            return None

        return ProcessMessageResult(
            messages=[
                f'You replied with: "{text}" to message ID: {replied_to_message_id}'
            ],
            status="success",
        )

        # TODO: add reply-specific logic here


# Global service instance
message_handler_service = MessageHandlerService()
