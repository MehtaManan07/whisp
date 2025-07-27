import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.communication.whatsapp.schema import HandleMessagePayload, ProcessMessageResult
from app.modules.users.dto import CreateUserDto
from app.modules.users.service import users_service
from app.utils.constants import WAKEUP_MESSAGES

logger = logging.getLogger(__name__)


class MessageHandlerService:
    def __init__(self):
        self.logger = logger

    async def handle_new_message(
        self, payload: HandleMessagePayload, db: AsyncSession
    ) -> Optional[ProcessMessageResult]:
        """Handle new incoming messages"""
        self.logger.info(f"Handling new message: {payload}")

        text = (
            payload.message.text.body.strip().lower() if payload.message.text else None
        )
        if not text:
            return None

        match text:
            case "wakeup":
                return await self.handle_wakeup_message(payload, db)

            # Placeholder for other commands like 'log', 'help', etc.
            # case "log":
            #     return await self.handle_log_command(payload, db)

            case _:
                # Default fallback
                return ProcessMessageResult(
                    messages=[
                        'Hmm, I didn\'t get that. Try "log" or "wakeup" to get started.'
                    ],
                    status="success",
                )

    async def handle_wakeup_message(
        self, payload: HandleMessagePayload, db: AsyncSession
    ) -> ProcessMessageResult:
        """Handle wakeup command"""
        user_data = await users_service.find_or_create(
            db=db,
            user_data=CreateUserDto(
                wa_id=payload.contact.wa_id,
                name=payload.contact.profile.get("name"),
                phone_number=payload.from_,
            ),
        )

        if not user_data:
            return ProcessMessageResult(
                messages=[
                    "Something went wrong while setting you up. Try again later."
                ],
                status="error",
            )

        message = (
            WAKEUP_MESSAGES.existing_user(user_data["user"].name)
            if user_data["is_existing_user"]
            else WAKEUP_MESSAGES.new_user(user_data["user"].name)
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
