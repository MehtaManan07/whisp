from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.intent_classifier.base_handler import BaseHandlers
from app.agents.intent_classifier.decorators import intent_handler
from app.modules.expenses.service import ExpensesService


class ExpenseHandlers(BaseHandlers):
    def __init__(self):
        super().__init__()
        self.service = ExpensesService()

    @intent_handler("log_expense")
    async def log_expense(self, intent_result, user_id: int, db: AsyncSession):
        print(intent_result, user_id)
        return {"entity": intent_result}