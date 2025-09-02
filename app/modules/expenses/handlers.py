from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.intent_classifier.base_handler import BaseHandlers
from app.agents.intent_classifier.decorators import intent_handler
from app.agents.intent_classifier.types import IntentType, IntentClassificationResult
from app.modules.expenses.service import ExpensesService


class ExpenseHandlers(BaseHandlers):
    def __init__(self):
        super().__init__()
        self.service = ExpensesService()

    @intent_handler(IntentType.LOG_EXPENSE)
    async def log_expense(
        self, intent_result: IntentClassificationResult, user_id: int, db: AsyncSession
    ) -> Dict[str, Any]:
        """Handle log expense intent."""
        return {"entity": intent_result}

    @intent_handler(IntentType.VIEW_EXPENSES)
    async def view_expenses(
        self, intent_result: IntentClassificationResult, user_id: int, db: AsyncSession
    ) -> Dict[str, Any]:
        """Handle view expenses intent."""
        return {"entity": intent_result}
