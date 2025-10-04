# """
# Main Message Processing Orchestrator

# This is the heart of the system - orchestrates the entire message flow:
# 1. Cache check
# 2. Context retrieval
# 3. Intent classification
# 4. Data extraction
# 5. Category classification
# 6. Intent handling
# 7. Response building

# This replaces your current modules/message_handler/service.py
# """

# from typing import Dict, Any, Optional
# import hashlib
# from datetime import datetime


# class MessageOrchestrator:
#     """
#     Orchestrates the complete message processing pipeline

#     Flow:
#     Message → Cache? → Context → Intent → Extract → Categorize → Handle → Respond
#     """

#     def __init__(
#         self,
#         intent_classifier: IntentClassifier,
#         extractor: OptimizedTwoStageExtractor,
#         category_classifier: CategoryClassifier,
#         intent_router: IntentRouter,
#         context_manager: ContextManager,
#         response_builder: ResponseBuilder,
#         user_service: UserService,
#         redis_client,
#     ):
#         self.intent_classifier = intent_classifier
#         self.extractor = extractor
#         self.categorizer = category_classifier
#         self.router = intent_router
#         self.context = context_manager
#         self.response_builder = response_builder
#         self.user_service = user_service
#         self.redis = redis_client

#         # Performance metrics
#         self.metrics = {
#             "total_messages": 0,
#             "cache_hits": 0,
#             "llm_calls": 0,
#             "avg_processing_time": [],
#         }

#     async def process_message(
#         self, phone_number: str, message_text: str, message_id: str
#     ) -> str:
#         """
#         Main entry point for processing a WhatsApp message

#         Args:
#             phone_number: User's WhatsApp number
#             message_text: The message content
#             message_id: WhatsApp message ID

#         Returns:
#             Response text to send back to user
#         """
#         start_time = datetime.now()
#         self.metrics["total_messages"] += 1

#         try:
#             # Step 1: Get or create user
#             user = await self.user_service.get_or_create_by_phone(phone_number)

#             # Step 2: Check if this is a duplicate message
#             if await self._is_duplicate(message_id):
#                 return await self._get_cached_response(message_id)

#             # Step 3: Check response cache (for identical messages)
#             if cached_response := await self._check_response_cache(
#                 user.id, message_text
#             ):
#                 self.metrics["cache_hits"] += 1
#                 return cached_response

#             # Step 4: Get conversation context
#             context = await self.context.get_context(user.id)

#             # Step 5: Handle special cases (commands, replies)
#             if special_response := await self._handle_special_cases(
#                 message_text, user, context
#             ):
#                 return special_response

#             # Step 6: Process with intelligence layer
#             result = await self._process_with_intelligence(message_text, user, context)

#             # Step 7: Build response
#             response_text = await self.response_builder.build(result, user, context)

#             # Step 8: Update context
#             await self.context.add_message(
#                 user.id,
#                 {
#                     "role": "user",
#                     "content": message_text,
#                     "timestamp": datetime.now().isoformat(),
#                     "result": result,
#                 },
#             )

#             # Step 9: Cache response
#             await self._cache_response(user.id, message_text, response_text, message_id)

#             # Track performance
#             processing_time = (datetime.now() - start_time).total_seconds()
#             self.metrics["avg_processing_time"].append(processing_time)

#             return response_text

#         except Exception as e:
#             # Error handling
#             await self._log_error(
#                 user.id if "user" in locals() else None, message_text, e
#             )
#             return "Sorry, I encountered an error processing your message. Please try again."

#     async def _process_with_intelligence(
#         self, message: str, user: Any, context: Dict
#     ) -> Dict[str, Any]:
#         """
#         Process message through intelligence layer

#         Returns structured result with intent, data, and metadata
#         """

#         # Step 1: Intent Classification (with pattern matching optimization)
#         intent_result = await self.intent_classifier.classify(message)

#         if intent_result["intent"] == "UNKNOWN":
#             return {
#                 "intent": "UNKNOWN",
#                 "confidence": intent_result["confidence"],
#                 "needs_clarification": True,
#             }

#         # Step 2: Data Extraction (dynamic schema loading)
#         extraction_result = await self.extractor.extract_for_intent(
#             intent=intent_result["intent"], message=message, context=context
#         )

#         # Step 3: Category Classification (if expense-related)
#         if intent_result["intent"] in ["LOG_EXPENSE", "VIEW_EXPENSES"]:
#             if extraction_result.get("data"):
#                 category_result = await self.categorizer.classify(
#                     merchant=extraction_result["data"].get("merchant"),
#                     description=extraction_result["data"].get("notes"),
#                     amount=extraction_result["data"].get("amount"),
#                     user_id=user.id,
#                 )

#                 # Merge category into extraction data
#                 if extraction_result["data"].get("category") is None:
#                     extraction_result["data"]["category"] = category_result["category"]
#                     extraction_result["data"]["subcategory"] = category_result[
#                         "subcategory"
#                     ]

#         # Step 4: Route to appropriate handler
#         handler_result = await self.router.route(
#             intent=intent_result["intent"],
#             data=extraction_result.get("data"),
#             user=user,
#             context=context,
#         )

#         return {
#             "intent": intent_result["intent"],
#             "data": extraction_result.get("data"),
#             "result": handler_result,
#             "confidence": extraction_result.get("confidence"),
#             "needs_clarification": extraction_result.get("needs_clarification", False),
#             "processing_method": extraction_result.get("processing_method"),
#         }

#     async def _handle_special_cases(
#         self, message: str, user: Any, context: Dict
#     ) -> Optional[str]:
#         """
#         Handle special cases before full processing:
#         - Commands (/help, /list, etc)
#         - Reply messages (clarifications)
#         - Simple greetings
#         """

#         # Commands
#         if message.startswith("/"):
#             return await self._handle_command(message, user)

#         # Reply to previous clarification
#         if context.get("pending_clarification"):
#             return await self._handle_clarification_reply(message, user, context)

#         # Simple greetings
#         if message.lower().strip() in ["hi", "hello", "hey", "start"]:
#             return (
#                 f"Hey {user.name or 'there'}! 👋\n\n"
#                 f"I'm your personal finance assistant. Just tell me what you spent, "
#                 f"and I'll track it for you.\n\n"
#                 f"Try: 'I spent 500 on groceries' or 'How much did I spend this month?'"
#             )

#         return None

#     async def _handle_command(self, command: str, user: Any) -> str:
#         """Handle slash commands"""

#         commands = {
#             "/help": self._command_help,
#             "/stats": self._command_stats,
#             "/list": self._command_list_recent,
#             "/budget": self._command_show_budgets,
#         }

#         cmd = command.split()[0].lower()
#         handler = commands.get(cmd)

#         if handler:
#             return await handler(user)

#         return "Unknown command. Try /help to see available commands."

#     async def _command_help(self, user: Any) -> str:
#         """Help command response"""
#         return """
# 📱 *Whisp Commands*

# 💰 *Track Expenses*
# Just tell me naturally:
# • "I spent 500 on groceries"
# • "Paid 1200 for rent today"
# • "Coffee at Starbucks for 6.50"

# 📊 *View Spending*
# • "How much did I spend this month?"
# • "Show my coffee expenses"
# • "Total spent on food this week"

# 🎯 *Budgets & Goals*
# • "Set 5000 budget for dining"
# • "Show my budgets"
# • "Set a goal to save 10000"

# ⚡ *Quick Commands*
# /list - Recent transactions
# /stats - Spending summary
# /budget - View budgets
# /help - This message
# """

#     async def _is_duplicate(self, message_id: str) -> bool:
#         """Check if we've already processed this message"""
#         key = f"processed_msg:{message_id}"
#         exists = await self.redis.exists(key)

#         if not exists:
#             # Mark as processed (expire after 1 hour)
#             await self.redis.setex(key, 3600, "1")

#         return exists

#     async def _get_cached_response(self, message_id: str) -> str:
#         """Get cached response for duplicate message"""
#         key = f"response:{message_id}"
#         response = await self.redis.get(key)
#         return


import logging
import random
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError, DatabaseError, ExternalServiceError
from app.intelligence.extraction.router import route_intent
from app.integrations.whatsapp.schema import HandleMessagePayload, ProcessMessageResult
from app.intelligence.extraction.extractor import Extractor
from app.intelligence.intent.classifier import IntentClassifier
from app.modules.users.dto import CreateUserDto
from app.core.db import User
import app.core.constants.whatsapp_responses as message_constants
from app.intelligence.intent.types import IntentType
from app.modules.users.service import UsersService

logger = logging.getLogger(__name__)


class MessageOrchestrator:
    """
    Central service for handling incoming WhatsApp messages.

    Routes messages based on type (command, reply, free text) and intent.
    """

    def __init__(
        self,
        users_service: UsersService,
        intent_classifier: IntentClassifier,
        extractor: Extractor,
    ):
        self.logger = logger
        self.users_service = users_service
        self.intent_classifier = intent_classifier
        self.extractor = extractor

    # =============================================================================
    # MAIN ENTRY POINT
    # =============================================================================

    async def handle_new_message(
        self, payload: HandleMessagePayload, db: AsyncSession
    ) -> Optional[ProcessMessageResult]:
        """Main entry point for handling new incoming messages"""
        self.logger.info(f"Handling new message: {payload}")

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
            return ProcessMessageResult(
                status="error",
                messages=[user_message]
            )

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

        intent = await self.intent_classifier.classify(text)

        if intent == IntentType.UNKNOWN:
            return ProcessMessageResult(
                messages=[random.choice(message_constants.unknown_responses)],
                status="success",
            )

        extracted_dto = await self.extractor.extract(
            message=text, intent=intent, user_id=user.id
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
            raise DatabaseError("ensure user", str(e))

    def _extract_text(self, payload: HandleMessagePayload) -> Optional[str]:
        """Extract and clean text from message payload"""
        if not payload.message.text:
            return None
        return payload.message.text.body.strip().lower()


# =============================================================================
# SERVICE INSTANCE
# =============================================================================
