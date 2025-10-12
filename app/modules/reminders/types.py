from enum import Enum
from typing import Optional, List
from pydantic import BaseModel


class ReminderType(str, Enum):
    """Types of reminders supported."""

    BILL = "bill"
    EXPENSE_LOG = "expense_log"
    CUSTOM = "custom"


class RecurrenceType(str, Enum):
    """Recurrence patterns for reminders."""

    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class RecurrenceConfig(BaseModel):
    """Configuration for recurring reminders."""

    time: Optional[str] = None  # HH:MM format
    days: Optional[List[int]] = None  # For weekly: [0-6] where 0=Monday
    day: Optional[int] = None  # For monthly: day of month (1-31)
    month: Optional[int] = None  # For yearly: month (1-12)

    class Config:
        json_schema_extra = {
            "examples": [
                {"time": "09:00"},
                {"days": [0, 2, 4], "time": "09:00"},
                {"day": 15, "time": "09:00"},
                {"month": 3, "day": 15, "time": "09:00"},
            ]
        }


class ReminderStatus(str, Enum):
    """Status of a reminder."""

    ACTIVE = "active"
    SNOOZED = "snoozed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
