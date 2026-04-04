from typing import Optional
from pydantic import BaseModel, Field


class CreateBudgetModel(BaseModel):
    user_id: int = Field(description="The user's ID")
    category_name: str = Field(description="Parent category name (e.g., Food & Dining, Transportation)")
    amount_limit: float = Field(description="Budget limit amount in rupees")
    period: str = Field(
        default="monthly",
        description="Budget period: 'weekly' or 'monthly'",
    )


class ViewBudgetsModel(BaseModel):
    user_id: int = Field(description="The user's ID")


class DeleteBudgetModel(BaseModel):
    user_id: int = Field(description="The user's ID")
    category_name: Optional[str] = Field(
        default=None,
        description="Parent category name of the budget to remove. Omit or set to 'all' to remove all budgets.",
    )
