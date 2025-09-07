import json
import logging
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from app.communication.llm.service import llm_service, LLMServiceError
import app.agents.intent_classifier.prompts as intent_classifier_prompts
from app.agents.intent_classifier.types import (
    CLASSIFIED_RESULT,
    DTO_UNION,
    INTENT_TO_DTO,
    IntentType,
)

logger = logging.getLogger(__name__)


class IntentClassifierAgent:
    def __init__(self):
        # No need to store API configuration since we use llm_service
        pass

    def _parse_intent(self, intent_str: str) -> IntentType:
        """Safely parse intent string to IntentType enum."""
        try:
            return IntentType(intent_str)
        except ValueError:
            logger.warning(
                f"Unknown intent string: {intent_str}, defaulting to UNKNOWN"
            )
            return IntentType.UNKNOWN

    async def classify(self, message: str) -> CLASSIFIED_RESULT:
        intent_prompt = intent_classifier_prompts.build_intent_prompt(message)

        try:
            # Use llm_service for the API call
            intent_response = await llm_service.complete(
                prompt=intent_prompt, max_tokens=500, temperature=0
            )

            intent_content = intent_response.content
            intent_parsed = json.loads(intent_content)

            intent = self._parse_intent(intent_parsed.get("intent", "unknown"))
            
            # Return early if intent is unknown - no need to calculate DTO
            if intent == IntentType.UNKNOWN:
                return None, IntentType.UNKNOWN
            
            dto_prompt = intent_classifier_prompts.build_dto_prompt(message, intent, 2)
            print("dto_prompt", dto_prompt)
            dto_response = await llm_service.complete(
                prompt=dto_prompt, max_tokens=500, temperature=0
            )
            print("dto_response", dto_response)
            dto_parsed = json.loads(dto_response.content)
            dto_instance = INTENT_TO_DTO[intent](**dto_parsed)
            print("dto_instance", dto_instance)

            return dto_instance, intent
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return None, IntentType.UNKNOWN
