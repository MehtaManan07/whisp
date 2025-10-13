from enum import Enum
from typing import Dict, Tuple, Type, Union
from pydantic import BaseModel

from app.modules.expenses.dto import CreateExpenseModel, GetAllExpensesModel
from app.modules.reminders.dto import CreateReminderDTO, ListRemindersDTO


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


DTO_UNION = Union[
    CreateExpenseModel, GetAllExpensesModel, CreateReminderDTO, ListRemindersDTO
]

INTENT_TO_DTO: Dict[IntentType, Type[DTO_UNION]] = {
    IntentType.LOG_EXPENSE: CreateExpenseModel,
    IntentType.VIEW_EXPENSES: GetAllExpensesModel,
    IntentType.SET_REMINDER: CreateReminderDTO,
    IntentType.VIEW_REMINDERS: ListRemindersDTO,
}

CLASSIFIED_RESULT = Tuple[DTO_UNION | None, IntentType]
