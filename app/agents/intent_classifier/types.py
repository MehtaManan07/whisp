from enum import Enum


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
