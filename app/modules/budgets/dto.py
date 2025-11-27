from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator

from app.modules.budgets.types import BudgetPeriod


class CreateBudgetDTO(BaseModel):
    """DTO for creating a new budget."""

    user_id: int = Field(..., description="ID of the user creating the budget")
    period: BudgetPeriod = Field(..., description="Budget time period (daily, weekly, monthly, yearly)")
    amount: float = Field(..., gt=0, description="Budget limit amount")
    category_name: Optional[str] = Field(None, description="Category name for budget (null = overall budget)")
    alert_thresholds: List[float] = Field(
        default=[80, 100],
        description="Alert thresholds in percentages (default: [80, 100])"
    )

    @field_validator("alert_thresholds")
    @classmethod
    def validate_thresholds(cls, v):
        """Validate alert thresholds are between 0 and 100."""
        if not v:
            return [80, 100]
        for threshold in v:
            if not (0 <= threshold <= 100):
                raise ValueError("Alert thresholds must be between 0 and 100")
        return sorted(v)  # Sort thresholds in ascending order

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "user_id": 1,
                    "period": "monthly",
                    "amount": 50000,
                    "category_name": None,
                    "alert_thresholds": [80, 100],
                },
                {
                    "user_id": 1,
                    "period": "weekly",
                    "amount": 5000,
                    "category_name": "food",
                    "alert_thresholds": [80, 100],
                },
            ]
        }


class UpdateBudgetDTO(BaseModel):
    """DTO for updating an existing budget."""

    budget_id: int = Field(..., description="ID of the budget to update")
    amount: Optional[float] = Field(None, gt=0, description="Updated budget amount")
    period: Optional[BudgetPeriod] = Field(None, description="Updated budget period")
    category_name: Optional[str] = Field(None, description="Updated category name")
    alert_thresholds: Optional[List[float]] = Field(None, description="Updated alert thresholds")
    is_active: Optional[bool] = Field(None, description="Whether the budget is active")

    @field_validator("alert_thresholds")
    @classmethod
    def validate_thresholds(cls, v):
        """Validate alert thresholds are between 0 and 100."""
        if v is None:
            return v
        for threshold in v:
            if not (0 <= threshold <= 100):
                raise ValueError("Alert thresholds must be between 0 and 100")
        return sorted(v)

    class Config:
        json_schema_extra = {
            "examples": [
                {"budget_id": 1, "amount": 60000},
                {"budget_id": 2, "is_active": False},
                {"budget_id": 3, "alert_thresholds": [50, 80, 100]},
            ]
        }


class GetBudgetDTO(BaseModel):
    """DTO for getting budgets with optional filters."""

    user_id: int = Field(..., description="ID of the user")
    category_name: Optional[str] = Field(None, description="Filter by category name")
    period: Optional[BudgetPeriod] = Field(None, description="Filter by period")
    is_active: Optional[bool] = Field(True, description="Filter by active status")

    class Config:
        json_schema_extra = {
            "examples": [
                {"user_id": 1, "is_active": True},
                {"user_id": 1, "category_name": "food", "period": "monthly"},
            ]
        }


class ViewBudgetProgressDTO(BaseModel):
    """DTO for viewing budget progress."""

    user_id: int = Field(..., description="ID of the user")
    category_name: Optional[str] = Field(None, description="Filter by category name")
    period: Optional[BudgetPeriod] = Field(None, description="Filter by period")

    class Config:
        json_schema_extra = {
            "examples": [
                {"user_id": 1},
                {"user_id": 1, "category_name": "food"},
                {"user_id": 1, "period": "monthly"},
            ]
        }


class DeleteBudgetDTO(BaseModel):
    """DTO for deleting a budget."""

    budget_id: int = Field(..., description="ID of the budget to delete")
    user_id: int = Field(..., description="ID of the user (for verification)")

    class Config:
        json_schema_extra = {
            "example": {"budget_id": 1, "user_id": 1}
        }


class BudgetResponseDTO(BaseModel):
    """DTO for budget responses."""

    id: int = Field(..., description="Unique identifier for the budget")
    user_id: int = Field(..., description="ID of the user who owns this budget")
    category_id: Optional[int] = Field(None, description="Associated category ID (null = overall budget)")
    category_name: Optional[str] = Field(None, description="Category name")
    period: BudgetPeriod = Field(..., description="Budget period")
    amount: float = Field(..., description="Budget limit amount")
    alert_thresholds: List[float] = Field(..., description="Alert thresholds in percentages")
    is_active: bool = Field(..., description="Whether the budget is active")
    created_at: datetime = Field(..., description="When the budget was created")
    updated_at: Optional[datetime] = Field(None, description="When the budget was last updated")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 1,
                "category_id": 5,
                "category_name": "Food",
                "period": "monthly",
                "amount": 50000,
                "alert_thresholds": [80, 100],
                "is_active": True,
                "created_at": "2025-11-27T10:00:00Z",
                "updated_at": None,
            }
        }


class BudgetProgressResponseDTO(BaseModel):
    """DTO for budget progress responses."""

    budget: BudgetResponseDTO = Field(..., description="Budget details")
    spent: float = Field(..., description="Amount spent in the budget period")
    remaining: float = Field(..., description="Amount remaining (negative if exceeded)")
    percentage: float = Field(..., description="Percentage of budget used")
    alerts_triggered: List[float] = Field(
        default=[],
        description="List of thresholds that have been crossed"
    )
    period_start: datetime = Field(..., description="Start of the budget period")
    period_end: datetime = Field(..., description="End of the budget period")

    class Config:
        json_schema_extra = {
            "example": {
                "budget": {
                    "id": 1,
                    "user_id": 1,
                    "category_id": 5,
                    "category_name": "Food",
                    "period": "monthly",
                    "amount": 50000,
                    "alert_thresholds": [80, 100],
                    "is_active": True,
                    "created_at": "2025-11-27T10:00:00Z",
                    "updated_at": None,
                },
                "spent": 42000,
                "remaining": 8000,
                "percentage": 84.0,
                "alerts_triggered": [80],
                "period_start": "2025-10-28T00:00:00Z",
                "period_end": "2025-11-27T23:59:59Z",
            }
        }


class BudgetListResponseDTO(BaseModel):
    """DTO for list of budgets."""

    budgets: List[BudgetResponseDTO] = Field(..., description="List of budget objects")
    total: int = Field(..., description="Total number of budgets")
    active_count: int = Field(..., description="Number of active budgets")

    class Config:
        json_schema_extra = {
            "example": {"budgets": [], "total": 5, "active_count": 3}
        }

