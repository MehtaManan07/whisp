from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from typing import Optional, Literal


class DeleteExpenseModel(BaseModel):
    id: int


class CreateExpenseModel(BaseModel):
    user_id: int
    category_name: Optional[str] = None
    subcategory_name: Optional[str] = None
    amount: float
    note: Optional[str] = None
    source_message_id: Optional[str] = None
    vendor: Optional[str] = None
    timestamp: Optional[datetime] = None


class GetAllExpensesModel(BaseModel):
    user_id: int
    category_name: Optional[str] = None
    vendor: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    subcategory_name: Optional[str] = None
    start_amount: Optional[float] = None
    end_amount: Optional[float] = None
    aggregation_type: Optional[Literal["sum", "count", "avg", "min", "max"]] = (
        None  # could have declared a type for this but swagger was not liking it
    )


class GetExpensesByCategoryModel(BaseModel):
    user_id: int
    category_id: int


ExpenseAggregationType = Literal["sum", "count", "avg", "min", "max"]


class ExpenseResponse(BaseModel):
    id: int
    user_id: int
    category_id: Optional[int]
    amount: float
    note: Optional[str]
    vendor: Optional[str]
    source_message_id: Optional[str]
    timestamp: datetime
    created_at: datetime
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime]

    category_name: Optional[str]  # <-- new field, from related model

    def to_human_message(self) -> str:
        """
        Returns a human-readable, natural language summary of the expense.
        """
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

        # Add date
        if self.timestamp:
            parts.append(f"on {self.timestamp.strftime('%B %d, %Y at %H:%M')}")

        # Add deleted info if present
        if self.deleted_at:
            parts.append(
                f"(deleted on {self.deleted_at.strftime('%B %d, %Y at %H:%M')})"
            )

        # # Add IDs for reference if needed
        # parts.append(f"[Expense ID: {self.id}]")

        return " ".join(parts)

    class Config:
        orm_mode = True
