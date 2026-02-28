import logging
import random
from typing import Optional

from app.core.exceptions import ValidationError, DatabaseError
from app.intelligence.extraction.router import route_intent
from app.integrations.whatsapp.schema import HandleMessagePayload, ProcessMessageResult
from app.intelligence.extraction.extractor import extract_dto
from app.intelligence.intent.classifier import IntentClassifier
from app.intelligence.categorization.classifier import CategoryClassifier
from app.modules.users.dto import CreateUserDto
from app.modules.users.models import User
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
        logger.info("Initializing MessageOrchestrator")
        self.users_service = users_service
        self.intent_classifier = intent_classifier
        self.llm_service = llm_service
        self.category_classifier = category_classifier

    # =============================================================================
    # MAIN ENTRY POINT
    # =============================================================================

    async def handle_new_message(
        self, payload: HandleMessagePayload
    ) -> Optional[ProcessMessageResult]:
        """Main entry point for handling new incoming messages."""
        try:
            user = await self._ensure_user(payload)

            text = self._extract_text(payload)
            if not text:
                return None

            if text.startswith("/"):
                return await self.handle_command(payload)
            elif payload.message.context:
                return await self.handle_reply(payload, user)
            else:
                return await self.handle_free_text(payload, user)
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}", exc_info=True)
            user_message = message_constants.get_user_friendly_error_message(e)
            return ProcessMessageResult(status="error", messages=[user_message])

    # MESSAGE TYPE HANDLERS
    # =============================================================================

    async def handle_command(
        self, payload: HandleMessagePayload
    ) -> Optional[ProcessMessageResult]:
        """Handle command messages (starting with /)."""
        text = self._extract_text(payload)
        if not text:
            return None

        match text:
            case "/help":
                return await self.handle_help_command(payload)
            case _:
                return ProcessMessageResult(
                    messages=[
                        'Unknown command. Try "/help" to see available commands.'
                    ],
                    status="success",
                )

    async def handle_free_text(
        self, payload: HandleMessagePayload, user: User
    ) -> Optional[ProcessMessageResult]:
        """Handle free text messages using intent classification."""
        text = self._extract_text(payload)
        if not text:
            return None

        # Non-reply messages should always follow normal intent flow.
        # Pending bank transaction handling is reply-context only.
        from app.core.dependencies import get_bank_transaction_service

        bank_transaction_service = get_bank_transaction_service()
        pending_items = await bank_transaction_service.get_all_pending_confirmations(
            user_wa_id=payload.contact.wa_id
        )

        if pending_items:
            self.logger.info(
                "Non-reply routed to normal intent flow despite pending transactions: user=%s pending_count=%d",
                payload.contact.wa_id,
                len(pending_items),
            )

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
            classified_result=classified_result,
            user_id=user.id,
        )

        return ProcessMessageResult(
            messages=[response],
            status="success",
        )

    async def handle_reply(
        self, payload: HandleMessagePayload, user: User
    ) -> Optional[ProcessMessageResult]:
        """Handle reply messages with pending-transaction context mapping."""
        text = self._extract_text(payload)
        replied_to_message_id = (
            payload.message.context.id if payload.message.context else None
        )

        if not text:
            return None

        from app.core.dependencies import get_bank_transaction_service

        bank_transaction_service = get_bank_transaction_service()
        pending_confirmation = await bank_transaction_service.get_pending_confirmation(
            user_wa_id=payload.contact.wa_id,
            replied_to_message_id=replied_to_message_id,
        )

        if pending_confirmation:
            self.logger.info(
                "Reply matched pending transaction: user=%s prompt_message_id=%s amount=%.2f",
                payload.contact.wa_id,
                replied_to_message_id,
                pending_confirmation.transaction_data.amount,
            )
            return await self.handle_pending_transaction_description(
                payload=payload,
                user=user,
                pending_confirmation=pending_confirmation,
                bank_transaction_service=bank_transaction_service,
            )

        self.logger.info(
            "Reply not matched to pending prompt; falling back to normal intent flow: user=%s prompt_message_id=%s",
            payload.contact.wa_id,
            replied_to_message_id,
        )
        return await self.handle_free_text(payload, user)

    # =============================================================================
    # COMMAND HANDLERS
    # =============================================================================

    async def handle_help_command(
        self, payload: HandleMessagePayload
    ) -> ProcessMessageResult:
        """Handle help command."""
        message = message_constants.HELP_MESSAGES.help(
            name=payload.contact.profile.get("name", "buddy")
        )
        return ProcessMessageResult(messages=[message], status="success")
    
    async def handle_pending_transaction_description(
        self,
        payload: HandleMessagePayload,
        user: User,
        pending_confirmation,
        bank_transaction_service,
    ) -> ProcessMessageResult:
        """Log a pending bank transaction using the user's free-text description."""
        text = self._extract_text(payload)
        if not text:
            return None

        if text in {"skip", "ignore", "no"}:
            self.logger.info(
                "User skipped pending transaction: user=%s gmail_message_id=%s",
                payload.contact.wa_id,
                pending_confirmation.gmail_message_id,
            )
            await bank_transaction_service.clear_pending_confirmation(
                payload.contact.wa_id,
                gmail_message_id=pending_confirmation.gmail_message_id,
                prompt_message_id=pending_confirmation.prompt_message_id,
            )
            await bank_transaction_service.mark_transaction_action(
                pending_confirmation.gmail_message_id, "dismissed"
            )
            return ProcessMessageResult(
                messages=["Okay, skipped this expense."], status="success"
            )

        synthetic_message = (
            f"I spent ₹{pending_confirmation.transaction_data.amount:,.2f} on {text}"
        )
        self.logger.info(
            "Building synthetic expense message: user=%s gmail_message_id=%s message=%s",
            payload.contact.wa_id,
            pending_confirmation.gmail_message_id,
            synthetic_message,
        )

        try:
            extracted_dto = await extract_dto(
                message=synthetic_message,
                intent=IntentType.LOG_EXPENSE,
                user_id=user.id,
                llm_service=self.llm_service,
                category_classifier=self.category_classifier,
            )
        except Exception:
            self.logger.warning(
                "Failed to extract dto from pending transaction description: user=%s gmail_message_id=%s",
                payload.contact.wa_id,
                pending_confirmation.gmail_message_id,
            )
            return ProcessMessageResult(
                messages=[
                    "Got it — can you tell me in a few words what it was for?"
                ],
                status="success",
            )

        extracted_dto.amount = pending_confirmation.transaction_data.amount
        if not extracted_dto.note:
            extracted_dto.note = text
        if not extracted_dto.vendor and pending_confirmation.transaction_data.merchant:
            extracted_dto.vendor = pending_confirmation.transaction_data.merchant
        if not extracted_dto.timestamp and pending_confirmation.transaction_data.transaction_date:
            extracted_dto.timestamp = pending_confirmation.transaction_data.transaction_date

        response = await route_intent(
            classified_result=(extracted_dto, IntentType.LOG_EXPENSE),
            user_id=user.id,
        )
        self.logger.info(
            "Expense routed successfully from pending transaction: user=%s gmail_message_id=%s amount=%.2f",
            payload.contact.wa_id,
            pending_confirmation.gmail_message_id,
            extracted_dto.amount,
        )

        await bank_transaction_service.clear_pending_confirmation(
            payload.contact.wa_id,
            gmail_message_id=pending_confirmation.gmail_message_id,
            prompt_message_id=pending_confirmation.prompt_message_id,
        )

        await bank_transaction_service.mark_transaction_action(
            pending_confirmation.gmail_message_id, "confirmed"
        )

        return ProcessMessageResult(messages=[response], status="success")

    # =============================================================================
    # HELPER METHODS
    # =============================================================================

    async def _ensure_user(self, payload: HandleMessagePayload):
        """Ensure user exists in database."""
        try:
            if not payload.contact or not payload.contact.wa_id:
                raise ValidationError("Invalid contact information in message payload")

            user_data = await self.users_service.find_or_create(
                user_data=CreateUserDto(
                    wa_id=payload.contact.wa_id,
                    phone_number=payload.from_,
                    name=payload.contact.profile.get("name", ""),
                    meta={"phone_number": payload.from_},
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
