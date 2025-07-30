from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ExpenseSchema(BaseModel):
    id: int
    user_id: int
    category_id: Optional[int]
    amount: float
    note: Optional[str]
    source_message_id: Optional[str]
    deleted_at: Optional[datetime]

    class Config:
        orm_mode = True
