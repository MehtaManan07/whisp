from dataclasses import dataclass
from enum import Enum
import json
from typing import Any, Dict, Optional


class IntentType(str, Enum):
    """Enumeration of supported intent types."""

    LOG_EXPENSE = "log_expense"
    VIEW_EXPENSES = "view_expenses"
    VIEW_EXPENSES_BY_CATEGORY = "view_expenses_by_category"
    SET_BUDGET = "set_budget"
    VIEW_BUDGET = "view_budget"
    SET_GOAL = "set_goal"
    SET_REMINDER = "set_reminder"
    VIEW_GOALS = "view_goals"
    VIEW_REMINDERS = "view_reminders"
    REPORT_REQUEST = "report_request"
    GREETING = "greeting"
    HELP = "help"
    UNKNOWN = "unknown"


class IntentModule(str, Enum):
    """Enumeration of supported intent routes."""

    EXPENSE = "expense"
    BUDGET = "budget"
    GOAL = "goal"
    REMINDER = "reminder"
    REPORT = "report"
    GREETING = "greeting"
    HELP = "help"
    UNKNOWN = "unknown"


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
