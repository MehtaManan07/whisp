from dataclasses import dataclass
from enum import Enum
import json
from typing import Any, Dict, Optional, Protocol, Tuple, Type, Union, runtime_checkable
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.expenses.dto import CreateExpenseModel, GetAllExpensesModel


class IntentType(str, Enum):
    """Enumeration of supported intent types."""

    LOG_EXPENSE = "log_expense"
    VIEW_EXPENSES = "view_expenses"
    SET_BUDGET = "set_budget"
    VIEW_BUDGET = "view_budget"
    SET_GOAL = "set_goal"
    SET_REMINDER = "set_reminder"
    VIEW_GOALS = "view_goals"
    VIEW_REMINDERS = "view_reminders"
    UNKNOWN = "unknown"


DTO_UNION = Union[CreateExpenseModel, GetAllExpensesModel]

INTENT_TO_DTO: Dict[IntentType, Type[DTO_UNION]] = {
    IntentType.LOG_EXPENSE: CreateExpenseModel,
    IntentType.VIEW_EXPENSES: GetAllExpensesModel,
}

CLASSIFIED_RESULT = Tuple[DTO_UNION | None, IntentType]
