from typing import TypedDict, Optional
from app.infra.db import Expense


class CreateExpenseResult(TypedDict):
    expense: Expense
