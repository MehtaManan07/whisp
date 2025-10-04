from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from app.intelligence.intent.base_handler import BaseHandlers
from app.intelligence.intent.decorators import intent_handler
from app.intelligence.intent.types import (
    CLASSIFIED_RESULT,
    IntentType,
)
from app.modules.expenses.dto import CreateExpenseModel, GetAllExpensesModel
from app.modules.expenses.service import ExpensesService


class ExpenseHandlers(BaseHandlers):
    def __init__(self):
        super().__init__()
        self.service = ExpensesService()

    @intent_handler(IntentType.LOG_EXPENSE)
    async def log_expense(
        self, classified_result: CLASSIFIED_RESULT, user_id: int, db: AsyncSession
    ) -> str:
        """Handle log expense intent."""
        dto_instance, intent = classified_result
        if not dto_instance:
            return intent.value
        if not isinstance(dto_instance, CreateExpenseModel):
            return "Invalid data for creating expense."
        if not dto_instance.user_id:
            dto_instance.user_id = user_id
        await self.service.create_expense(db=db, data=dto_instance)
        return intent.value

    @intent_handler(IntentType.VIEW_EXPENSES)
    async def view_expenses(
        self, classified_result: CLASSIFIED_RESULT, user_id: int, db: AsyncSession
    ) -> str:
        """Handle view expenses intent."""
        dto_instance, intent = classified_result
        if not dto_instance:
            return intent.value
        if not isinstance(dto_instance, GetAllExpensesModel):
            return "Invalid data for viewing expenses."
        if not dto_instance.user_id:
            dto_instance.user_id = user_id
        expenses = await self.service.get_expenses(db=db, data=dto_instance)
        if not expenses:
            return "Wow, you have absolutely no expenses. Impressive budgeting, or just not tracking anything?"
        return "\n".join(str(expense) for expense in expenses)
