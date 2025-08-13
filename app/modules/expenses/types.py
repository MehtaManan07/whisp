from typing import TypedDict, Optional
from app.core.db import Expense


class CreateExpenseResult(TypedDict):
    expense: Expense
