from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class ReminderType(str, Enum):
    """Types of reminders supported."""

    BILL = "bill"  # Reminders for bills that need to be paid
    EXPENSE_LOG = "expense_log"  # Reminders to log daily expenses
    CUSTOM = "custom"  # Custom user-defined reminders


class RecurrenceType(str, Enum):
    """Recurrence patterns for reminders."""

    ONCE = "once"  # Reminder occurs only once
    DAILY = "daily"  # Reminder occurs every day
    WEEKLY = "weekly"  # Reminder occurs every week
    MONTHLY = "monthly"  # Reminder occurs every month
    YEARLY = "yearly"  # Reminder occurs every year


class RecurrenceConfig(BaseModel):
    """Configuration for recurring reminders."""

    time: Optional[str] = Field(None, description="Time to trigger reminder in HH:MM format (24-hour)")
    days: Optional[List[int]] = Field(None, description="Days for weekly recurrence where 0=Monday to 6=Sunday")
    day: Optional[int] = Field(None, description="Day of month for monthly recurrence (1-31)")
    month: Optional[int] = Field(None, description="Month for yearly recurrence (1-12)")

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

    ACTIVE = "active"  # Reminder is active and will trigger
    SNOOZED = "snoozed"  # Reminder is temporarily snoozed
    COMPLETED = "completed"  # Reminder has been completed
    CANCELLED = "cancelled"  # Reminder has been cancelled
