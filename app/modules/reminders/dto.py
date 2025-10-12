# app/modules/reminders/dto.py

from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator

from app.modules.reminders.types import ReminderType, RecurrenceType, RecurrenceConfig


class CreateReminderDTO(BaseModel):
    """DTO for creating a new reminder."""

    reminder_type: ReminderType = Field(..., description="Type of reminder")
    title: str = Field(..., min_length=1, max_length=200, description="Reminder title")
    description: Optional[str] = Field(None, description="Additional details")
    amount: Optional[Decimal] = Field(
        None, ge=0, description="Amount for bill reminders"
    )
    category_id: Optional[int] = Field(None, description="Associated category ID")

    recurrence_type: RecurrenceType = Field(
        ..., description="How often reminder repeats"
    )
    recurrence_config: Optional[RecurrenceConfig] = Field(
        None, description="Recurrence configuration"
    )

    next_trigger_at: Optional[datetime] = Field(
        None, description="When to first trigger (defaults to now)"
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v, info):
        """Validate amount is provided for bill reminders."""
        if info.data.get("reminder_type") == ReminderType.BILL and v is None:
            raise ValueError("Amount is required for bill reminders")
        return v

    @field_validator("recurrence_config")
    @classmethod
    def validate_recurrence_config(cls, v, info):
        """Validate recurrence config matches recurrence type."""
        recurrence_type = info.data.get("recurrence_type")

        if recurrence_type == RecurrenceType.ONCE:
            return None

        if recurrence_type != RecurrenceType.ONCE and v is None:
            raise ValueError(
                f"Recurrence config required for {recurrence_type} reminders"
            )

        # Validate weekly config
        if recurrence_type == RecurrenceType.WEEKLY:
            if not v.days or not isinstance(v.days, list):
                raise ValueError("Weekly reminders require 'days' list (0-6)")
            if not all(0 <= day <= 6 for day in v.days):
                raise ValueError("Days must be between 0 (Monday) and 6 (Sunday)")

        # Validate monthly config
        if recurrence_type == RecurrenceType.MONTHLY:
            if not v.day:
                raise ValueError("Monthly reminders require 'day' (1-31)")
            if not (1 <= v.day <= 31):
                raise ValueError("Day must be between 1 and 31")

        # Validate yearly config
        if recurrence_type == RecurrenceType.YEARLY:
            if not v.month or not v.day:
                raise ValueError("Yearly reminders require 'month' and 'day'")
            if not (1 <= v.month <= 12):
                raise ValueError("Month must be between 1 and 12")
            if not (1 <= v.day <= 31):
                raise ValueError("Day must be between 1 and 31")

        # Validate time format if provided
        if v.time:
            try:
                hours, minutes = map(int, v.time.split(":"))
                if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                    raise ValueError("Time must be in HH:MM format (00:00-23:59)")
            except (ValueError, AttributeError):
                raise ValueError("Time must be in HH:MM format")

        return v

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "reminder_type": "bill",
                    "title": "Electricity Bill",
                    "amount": 2000.00,
                    "recurrence_type": "monthly",
                    "recurrence_config": {"day": 15, "time": "09:00"},
                },
                {
                    "reminder_type": "expense_log",
                    "title": "Daily Expense Check-in",
                    "recurrence_type": "daily",
                    "recurrence_config": {"time": "21:00"},
                },
                {
                    "reminder_type": "custom",
                    "title": "Review monthly budget",
                    "description": "Check spending vs budget",
                    "recurrence_type": "monthly",
                    "recurrence_config": {"day": 1, "time": "10:00"},
                },
            ]
        }


class UpdateReminderDTO(BaseModel):
    """DTO for updating an existing reminder."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    amount: Optional[Decimal] = Field(None, ge=0)
    category_id: Optional[int] = None

    recurrence_type: Optional[RecurrenceType] = None
    recurrence_config: Optional[RecurrenceConfig] = None

    is_active: Optional[bool] = None

    @field_validator("recurrence_config")
    @classmethod
    def validate_recurrence_config(cls, v, info):
        """Validate recurrence config if provided."""
        if v is None:
            return v

        recurrence_type = info.data.get("recurrence_type")
        if not recurrence_type:
            return v

        # Same validation as CreateReminderDTO
        if recurrence_type == RecurrenceType.WEEKLY and (
            not v.days or not isinstance(v.days, list)
        ):
            raise ValueError("Weekly reminders require 'days' list")

        if recurrence_type == RecurrenceType.MONTHLY and not v.day:
            raise ValueError("Monthly reminders require 'day'")

        if recurrence_type == RecurrenceType.YEARLY and (not v.month or not v.day):
            raise ValueError("Yearly reminders require 'month' and 'day'")

        return v

    class Config:
        json_schema_extra = {
            "examples": [
                {"title": "Updated Electricity Bill", "amount": 2500.00},
                {"is_active": False},
                {"recurrence_config": {"day": 20, "time": "10:00"}},
            ]
        }


class ReminderResponseDTO(BaseModel):
    """DTO for reminder responses."""

    id: int
    user_id: int
    reminder_type: ReminderType
    title: str
    description: Optional[str]
    amount: Optional[Decimal]
    category_id: Optional[int]

    recurrence_type: RecurrenceType
    recurrence_config: Optional[dict]

    next_trigger_at: datetime
    last_triggered_at: Optional[datetime]

    is_active: bool

    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 1,
                "reminder_type": "bill",
                "title": "Electricity Bill",
                "description": None,
                "amount": 2000.00,
                "category_id": 1,
                "recurrence_type": "monthly",
                "recurrence_config": {"day": 15, "time": "09:00"},
                "next_trigger_at": "2025-11-15T09:00:00Z",
                "last_triggered_at": "2025-10-15T09:00:00Z",
                "is_active": True,
                "created_at": "2025-10-12T10:00:00Z",
                "updated_at": "2025-10-12T10:00:00Z",
            }
        }


class SnoozeReminderDTO(BaseModel):
    """DTO for snoozing a reminder."""

    duration_minutes: int = Field(
        ..., ge=1, description="How long to snooze in minutes"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {"duration_minutes": 60},  # 1 hour
                {"duration_minutes": 1440},  # 1 day
                {"duration_minutes": 10080},  # 1 week
            ]
        }


class ReminderListResponseDTO(BaseModel):
    """DTO for list of reminders."""

    reminders: list[ReminderResponseDTO]
    total: int
    active_count: int

    class Config:
        json_schema_extra = {
            "example": {"reminders": [], "total": 10, "active_count": 8}
        }
