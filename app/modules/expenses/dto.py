from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Literal


class DeleteExpenseModel(BaseModel):
    id: int = Field(..., description="Unique identifier of the expense to delete")


class CreateExpenseModel(BaseModel):
    user_id: int = Field(..., description="ID of the user creating the expense")
    category_name: Optional[str] = Field(None, description="Name of the category for this expense")
    subcategory_name: Optional[str] = Field(None, description="Name of the subcategory for this expense")
    amount: float = Field(..., description="Amount spent in the transaction")
    note: Optional[str] = Field(None, description="Additional notes or details about the expense")
    source_message_id: Optional[str] = Field(None, description="ID of the source message (e.g., from WhatsApp)")
    vendor: Optional[str] = Field(None, description="Name of the vendor or merchant")
    timestamp: Optional[datetime] = Field(None, description="When the expense occurred")


class GetAllExpensesModel(BaseModel):
    user_id: int = Field(..., description="ID of the user")
    category_name: Optional[str] = Field(None, description="Filter by category name")
    vendor: Optional[str] = Field(None, description="Filter by vendor name")
    start_date: Optional[str] = Field(None, description="Filter expenses from this date (ISO format)")
    end_date: Optional[str] = Field(None, description="Filter expenses until this date (ISO format)")
    subcategory_name: Optional[str] = Field(None, description="Filter by subcategory name")
    start_amount: Optional[float] = Field(None, description="Filter expenses with minimum amount")
    end_amount: Optional[float] = Field(None, description="Filter expenses with maximum amount")
    note: Optional[str] = Field(None, description="Filter by note content (case-insensitive partial match)")
    aggregation_type: Optional[Literal["sum", "count", "avg", "min", "max"]] = Field(
        None, description="Type of aggregation to apply (sum, count, avg, min, max)"
    )


class GetExpensesByCategoryModel(BaseModel):
    user_id: int = Field(..., description="ID of the user")
    category_id: int = Field(..., description="ID of the category to fetch expenses for")


ExpenseAggregationType = Literal["sum", "count", "avg", "min", "max"]


class ExpenseResponse(BaseModel):
    id: int = Field(..., description="Unique identifier for the expense")
    user_id: int = Field(..., description="ID of the user who owns this expense")
    category_id: Optional[int] = Field(None, description="Associated category ID")
    amount: float = Field(..., description="Amount of the expense")
    note: Optional[str] = Field(None, description="Additional notes about the expense")
    vendor: Optional[str] = Field(None, description="Vendor or merchant name")
    source_message_id: Optional[str] = Field(None, description="Source message ID (e.g., from WhatsApp)")
    timestamp: datetime = Field(..., description="When the expense occurred")
    created_at: datetime = Field(..., description="When the expense record was created")
    updated_at: Optional[datetime] = Field(None, description="When the expense record was last updated")
    deleted_at: Optional[datetime] = Field(None, description="When the expense was deleted (if applicable)")
    category_name: Optional[str] = Field(None, description="Name of the category for this expense")

    def to_human_message(self, user_timezone: str = "UTC") -> str:
        """
        Returns a human-readable, natural language summary of the expense.
        
        Args:
            user_timezone: User's IANA timezone for displaying times
        """
        from app.utils.datetime import format_datetime_for_user
        
        parts = []

        # Start with the main action
        amount_str = f"₹{self.amount:,.2f}"
        if self.category_name:
            main = f"You spent {amount_str} on {self.category_name}"
        elif self.category_id:
            main = f"You spent {amount_str} (category ID: {self.category_id})"
        else:
            main = f"You spent {amount_str}"
        if self.vendor:
            main += f" at {self.vendor}"
        parts.append(main)

        # Add note if present
        if self.note:
            parts.append(f'Note: "{self.note}"')

        # Add date (in user's timezone)
        if self.timestamp:
            date_str = format_datetime_for_user(self.timestamp, user_timezone, '%B %d, %Y at %I:%M %p')
            parts.append(f"on {date_str}")

        # Add deleted info if present
        if self.deleted_at:
            deleted_str = format_datetime_for_user(self.deleted_at, user_timezone, '%B %d, %Y at %I:%M %p')
            parts.append(f"(deleted on {deleted_str})")

        # # Add IDs for reference if needed
        # parts.append(f"[Expense ID: {self.id}]")

        return " ".join(parts)

    class Config:
        orm_mode = True
