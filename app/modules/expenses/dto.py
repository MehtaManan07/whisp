from pydantic import BaseModel
from typing import Optional, Dict, Any


class CreateExpenseModel(BaseModel):
    user_id: int
    category_name: Optional[str] = None
    subcategory_name: Optional[str] = None
    amount: float
    note: Optional[str] = None
    source_message_id: Optional[str] = None
