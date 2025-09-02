import logging
import random
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession


from app.agents.intent_classifier.router import route_intent
from app.communication.whatsapp.schema import HandleMessagePayload, ProcessMessageResult
from app.modules.users.dto import CreateUserDto
from app.core.db import User
from app.modules.users.service import users_service
import app.core.constants.whatsapp_responses as message_constants
from app.agents.intent_classifier import IntentClassifierAgent, IntentType

logger = logging.getLogger(__name__)


class MessageHandlerService:
    """
    Central service for handling incoming WhatsApp messages.

    Routes messages based on type (command, reply, free text) and intent.
    """

    def __init__(self):
        self.logger = logger

    # =============================================================================
    # MAIN ENTRY POINT
    # =============================================================================

    async def handle_new_message(
        self, payload: HandleMessagePayload, db: AsyncSession
    ) -> Optional[ProcessMessageResult]:
        """Main entry point for handling new incoming messages"""
        self.logger.info(f"Handling new message: {payload}")

        # Ensure user exists in DB
        user = await self._ensure_user(payload, db)

        # Extract and validate text
        text = self._extract_text(payload)
        if not text:
            return None

        # Route based on message type
        if text.startswith("/"):
            return await self.handle_command(payload, db)
        elif payload.message.context:
            return await self.handle_reply(payload, db)
        else:
            return await self.handle_free_text(payload, db, user)

    # =============================================================================
    # MESSAGE TYPE HANDLERS
    # =============================================================================

    async def handle_command(
        self, payload: HandleMessagePayload, db: AsyncSession
    ) -> Optional[ProcessMessageResult]:
        """Handle command messages (starting with /)"""
        text = self._extract_text(payload)
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
        self, payload: HandleMessagePayload, db: AsyncSession, user: User
    ) -> Optional[ProcessMessageResult]:
        """
        Handle free text messages using intent classification

        Flow:
        → classify intent (expense logging / reflection / chat)
        → if expense → parse it → log to DB → return friendly reply
        → if reflection → store it → generate LLM summary
        → else → fallback to LLM (generic chat)
        """
        text = self._extract_text(payload)
        if not text:
            return None

        # Classify intent
        intent_classifier_agent = IntentClassifierAgent()
        intent_result = await intent_classifier_agent.classify(text)
        response = await route_intent(
            intent_result=intent_result, user_id=user.id, db=db
        )

        if intent_result.intent == IntentType.UNKNOWN:
            return ProcessMessageResult(
                messages=[random.choice(message_constants.unknown_responses)],
                status="success",
            )

        # Default fallback for free text
        return ProcessMessageResult(
            messages=[f"Your intent is {intent_result.to_json()}"],
            status="success",
        )

    async def handle_reply(
        self, payload: HandleMessagePayload, db: AsyncSession
    ) -> Optional[ProcessMessageResult]:
        """Handle reply messages"""
        text = self._extract_text(payload)
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

    # =============================================================================
    # COMMAND HANDLERS
    # =============================================================================

    async def handle_help_command(
        self, payload: HandleMessagePayload, db: AsyncSession
    ) -> ProcessMessageResult:
        """Handle help command"""
        message = message_constants.HELP_MESSAGES.help(
            name=payload.contact.profile.get("name", "buddy")
        )
        return ProcessMessageResult(messages=[message], status="success")

    # =============================================================================
    # HELPER METHODS
    # =============================================================================

    async def _ensure_user(self, payload: HandleMessagePayload, db: AsyncSession):
        """Ensure user exists in database"""
        user_data = await users_service.find_or_create(
            db=db,
            user_data=CreateUserDto(
                wa_id=payload.contact.wa_id,
                phone_number=payload.from_,
                name=payload.contact.profile.get("name", ""),
            ),
        )
        return user_data["user"]

    def _extract_text(self, payload: HandleMessagePayload) -> Optional[str]:
        """Extract and clean text from message payload"""
        if not payload.message.text:
            return None
        return payload.message.text.body.strip().lower()


# =============================================================================
# SERVICE INSTANCE
# =============================================================================

# Global service instance
message_handler_service = MessageHandlerService()
