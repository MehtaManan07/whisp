import logging
import random
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError, DatabaseError
from app.intelligence.extraction.router import route_intent
from app.integrations.whatsapp.schema import HandleMessagePayload, ProcessMessageResult
from app.intelligence.extraction.extractor import extract_dto
from app.intelligence.intent.classifier import IntentClassifier
from app.intelligence.categorization.classifier import CategoryClassifier
from app.modules.users.dto import CreateUserDto
from app.core.db import User
import app.core.constants.whatsapp_responses as message_constants
from app.intelligence.intent.types import IntentType
from app.modules.users.service import UsersService

logger = logging.getLogger(__name__)


class MessageOrchestrator:
    """Central service for handling incoming WhatsApp messages."""

    def __init__(
        self,
        users_service: UsersService,
        intent_classifier: IntentClassifier,
        llm_service,
        category_classifier: CategoryClassifier,
    ):
        self.logger = logger
        self.users_service = users_service
        self.intent_classifier = intent_classifier
        self.llm_service = llm_service
        self.category_classifier = category_classifier

    # =============================================================================
    # MAIN ENTRY POINT
    # =============================================================================

    async def handle_new_message(
        self, payload: HandleMessagePayload, db: AsyncSession
    ) -> Optional[ProcessMessageResult]:
        """Main entry point for handling new incoming messages."""
        try:
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
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}", exc_info=True)
            # Get user-friendly error message from the actual error
            user_message = message_constants.get_user_friendly_error_message(e)
            return ProcessMessageResult(status="error", messages=[user_message])

    # MESSAGE TYPE HANDLERS
    # =============================================================================

    async def handle_command(
        self, payload: HandleMessagePayload, db: AsyncSession
    ) -> Optional[ProcessMessageResult]:
        """Handle command messages (starting with /)."""
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
        """Handle free text messages using intent classification."""
        text = self._extract_text(payload)
        if not text:
            return None

        intent = await self.intent_classifier.classify(text)

        if intent == IntentType.UNKNOWN:
            return ProcessMessageResult(
                messages=[random.choice(message_constants.unknown_responses)],
                status="success",
            )

        extracted_dto = await extract_dto(
            message=text,
            intent=intent,
            user_id=user.id,
            llm_service=self.llm_service,
            category_classifier=self.category_classifier,
        )
        classified_result = (extracted_dto, intent)

        response = await route_intent(
            classified_result=classified_result, user_id=user.id, db=db
        )

        # Default fallback for free text
        return ProcessMessageResult(
            messages=[response],
            status="success",
        )

    async def handle_reply(
        self, payload: HandleMessagePayload, db: AsyncSession
    ) -> Optional[ProcessMessageResult]:
        """Handle reply messages."""
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
        """Handle help command."""
        message = message_constants.HELP_MESSAGES.help(
            name=payload.contact.profile.get("name", "buddy")
        )
        return ProcessMessageResult(messages=[message], status="success")

    # =============================================================================
    # HELPER METHODS
    # =============================================================================

    async def _ensure_user(self, payload: HandleMessagePayload, db: AsyncSession):
        """Ensure user exists in database."""
        try:
            if not payload.contact or not payload.contact.wa_id:
                raise ValidationError("Invalid contact information in message payload")

            user_data = await self.users_service.find_or_create(
                db=db,
                user_data=CreateUserDto(
                    wa_id=payload.contact.wa_id,
                    phone_number=payload.from_,
                    name=payload.contact.profile.get("name", ""),
                ),
            )
            return user_data["user"]
        except Exception as e:
            self.logger.error(f"Error ensuring user exists: {str(e)}")
            raise DatabaseError(f"ensure user: {str(e)}")

    def _extract_text(self, payload: HandleMessagePayload) -> Optional[str]:
        """Extract and clean text from message payload."""
        if not payload.message.text:
            return None
        return payload.message.text.body.strip().lower()

