import json
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
from app.communication.llm.service import llm_service, LLMServiceError
import app.agents.intent_classifier.prompts as intent_classifier_prompts
from app.agents.intent_classifier.types import IntentClassificationResult, IntentType

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

    async def classify(self, message: str) -> IntentClassificationResult:
        intent_prompt = intent_classifier_prompts.build_intent_prompt(message)

        try:
            # Use llm_service for the API call
            intent_response = await llm_service.complete(
                prompt=intent_prompt, max_tokens=500, temperature=0
            )

            intent_content = intent_response.content
            intent_parsed = json.loads(intent_content)

            intent = self._parse_intent(intent_parsed.get("intent", "unknown"))
            dto_prompt = intent_classifier_prompts.build_dto_prompt(message, intent, 2)
            dto_response = await llm_service.complete(
                prompt=dto_prompt, max_tokens=500, temperature=0
            )
            dto_content = dto_response.content
            dto_parsed = json.loads(dto_content)
            # confidence = float(intent_parsed.get("confidence", 0.0))

            return IntentClassificationResult(
                intent=intent,
                confidence=1.0,
                raw=dto_parsed,
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return IntentClassificationResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                raw=None,
            )
        except LLMServiceError as e:
            logger.error(f"LLM service error during intent classification: {e}")
            return IntentClassificationResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                raw=None,
            )
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return IntentClassificationResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                raw=None,
            )
