from pydantic import BaseModel
from typing import Optional, Dict, Any


class CreateExpenseModel(BaseModel):
    user_id: int
    category_name: Optional[str] = None
    subcategory_name: Optional[str] = None
    amount: float
    note: Optional[str] = None
    source_message_id: Optional[str] = None


class DeleteExpenseModel(BaseModel):
    id: int


class GetAllExpensesModel(BaseModel):
    user_id: int


class GetExpensesByCategoryModel(BaseModel):
    user_id: int
    category_id: int


class GetMonthlyTotalModel(BaseModel):
    user_id: int
    month: int
    year: int