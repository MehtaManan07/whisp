import json
import logging
from typing import Dict, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from app.communication.llm.service import llm_service, LLMServiceError

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Enumeration of supported intent types."""
    LOG_EXPENSE = "log_expense"
    SET_BUDGET = "set_budget"
    VIEW_BUDGET = "view_budget"
    VIEW_EXPENSES = "view_expenses"
    SET_GOAL = "set_goal"
    SET_REMINDER = "set_reminder"
    VIEW_GOALS = "view_goals"
    VIEW_REMINDERS = "view_reminders"
    REPORT_REQUEST = "report_request"
    GREETING = "greeting"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class IntentClassificationResult:
    """Result of intent classification."""
    intent: IntentType
    confidence: float
    entities: Dict[str, Any]
    raw: Optional[str] = None


class IntentClassifierAgent:
    def __init__(self):
        # No need to store API configuration since we use llm_service
        pass

    def _parse_intent(self, intent_str: str) -> IntentType:
        """Safely parse intent string to IntentType enum."""
        try:
            return IntentType(intent_str)
        except ValueError:
            logger.warning(f"Unknown intent string: {intent_str}, defaulting to UNKNOWN")
            return IntentType.UNKNOWN

    def build_prompt(self, message: str) -> str:
        current_date = datetime.now().strftime("%Y-%m-%d")

        return f"""
You are an intent classification assistant for a personal finance chatbot.

Your job is to classify the user's message into one of the following high-level intents:

- "log_expense"
- "view_expenses"
- "view_expenses_by_category"
- "set_budget"
- "view_budget"
- "view_expenses"
- "set_goal"
- "set_reminder"
- "view_goals"
- "view_reminders"
- "report_request"
- "greeting"
- "help"
- "unknown"

Only return a JSON object with fields:
- "intent": string (one of the above)
- "confidence": number between 0 and 1
- "entities": (optional) any extracted fields like amount, category, date, etc.

Today's date is {current_date}.

User Message:
\"\"\"{message}\"\"\"
        
Return JSON only. Do not add any explanation.
"""

    async def classify(
        self, message: str
    ) -> IntentClassificationResult:
        prompt = self.build_prompt(message)

        try:
            # Use llm_service for the API call
            response = await llm_service.complete(
                prompt=prompt, max_tokens=500, temperature=0
            )

            content = response.content
            parsed = json.loads(content)

            intent_str = parsed.get("intent", "unknown")
            confidence = float(parsed.get("confidence", 0.0))
            entities = parsed.get("entities", {})

            return IntentClassificationResult(
                intent=self._parse_intent(intent_str),
                confidence=confidence,
                entities=entities,
                raw=content,
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return IntentClassificationResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                entities={},
                raw=None,
            )
        except LLMServiceError as e:
            logger.error(f"LLM service error during intent classification: {e}")
            return IntentClassificationResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                entities={},
                raw=None,
            )
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return IntentClassificationResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                entities={},
                raw=None,
            )
