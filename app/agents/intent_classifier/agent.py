import json
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
from app.communication.llm.service import llm_service, LLMServiceError
import app.agents.intent_classifier.prompts as intent_classifier_prompts
from app.agents.intent_classifier.types import IntentType, IntentModule

logger = logging.getLogger(__name__)


@dataclass
class IntentClassificationResult:
    """Result of intent classification."""

    intent: IntentType
    module: IntentModule
    confidence: float
    entities: Dict[str, Any]
    raw: Optional[str] = None

    def to_json(self) -> str:
        """Convert the result to a stringified JSON representation."""
        return json.dumps(
            {
                "intent": self.intent.value,
                "module": self.module.value,
                "confidence": self.confidence,
                "entities": self.entities,
                "raw": self.raw,
            },
            ensure_ascii=False,
        )


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

    def _parse_module(self, module_str: str) -> IntentModule:
        """Safely parse module string to IntentModule enum."""
        try:
            return IntentModule(module_str)
        except ValueError:
            logger.warning(f"Unknown module string: {module_str}, defaulting to UNKNOWN")
            return IntentModule.UNKNOWN

    async def classify(self, message: str) -> IntentClassificationResult:
        prompt = intent_classifier_prompts.build_prompt(message)

        try:
            # Use llm_service for the API call
            response = await llm_service.complete(
                prompt=prompt, max_tokens=500, temperature=0
            )

            content = response.content
            parsed = json.loads(content)

            intent_str = parsed.get("intent", "unknown")
            module_str = parsed.get("module", "unknown")
            confidence = float(parsed.get("confidence", 0.0))
            entities = parsed.get("entities", {})

            return IntentClassificationResult(
                intent=self._parse_intent(intent_str),
                confidence=confidence,
                entities=entities,
                raw=content,
                module=self._parse_module(module_str),
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return IntentClassificationResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                entities={},
                raw=None,
                module=IntentModule.UNKNOWN,
            )
        except LLMServiceError as e:
            logger.error(f"LLM service error during intent classification: {e}")
            return IntentClassificationResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                entities={},
                raw=None,
                module=IntentModule.UNKNOWN,
            )
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return IntentClassificationResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                entities={},
                raw=None,
                module=IntentModule.UNKNOWN,
            )
