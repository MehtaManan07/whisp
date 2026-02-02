from enum import Enum
from typing import Dict, Tuple, Type, Union
from pydantic import BaseModel

from app.modules.expenses.dto import CreateExpenseModel, GetAllExpensesModel, CorrectExpenseModel
from app.modules.reminders.dto import (
    CreateReminderDTO,
    ListRemindersDTO,
    UpdateReminderDTO,
)


class IntentType(str, Enum):
    """Enumeration of supported intent types."""

    LOG_EXPENSE = "log_expense"  # Intent to log a new expense
    VIEW_EXPENSES = "view_expenses"  # Intent to view or filter expenses
    CORRECT_EXPENSE = "correct_expense"  # Intent to correct/update an expense category
    SET_GOAL = "set_goal"  # Intent to set a financial goal (not yet implemented)
    SET_REMINDER = "set_reminder"  # Intent to create or set a reminder
    VIEW_GOALS = "view_goals"  # Intent to view financial goals (not yet implemented)
    VIEW_REMINDERS = "view_reminders"  # Intent to view or list reminders
    EDIT_REMINDER = "edit_reminder"  # Intent to edit a reminder
    UNKNOWN = "unknown"  # Intent could not be determined


DTO_UNION = Union[
    CreateExpenseModel,
    GetAllExpensesModel,
    CorrectExpenseModel,
    CreateReminderDTO,
    ListRemindersDTO,
    UpdateReminderDTO,
]

INTENT_TO_DTO: Dict[IntentType, Type[DTO_UNION]] = {
    IntentType.LOG_EXPENSE: CreateExpenseModel,
    IntentType.VIEW_EXPENSES: GetAllExpensesModel,
    IntentType.CORRECT_EXPENSE: CorrectExpenseModel,
    IntentType.SET_REMINDER: CreateReminderDTO,
    IntentType.VIEW_REMINDERS: ListRemindersDTO,
    IntentType.EDIT_REMINDER: UpdateReminderDTO,
}

CLASSIFIED_RESULT = Tuple[DTO_UNION | None, IntentType]
