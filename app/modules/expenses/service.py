from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, Literal, Optional

from app.agents.intent_classifier.agent import IntentClassifierAgent
from app.core.db import Expense
from app.modules.expenses.dto import CreateExpenseModel
from app.modules.categories.service import CategoriesService
import logging

from app.utils.datetime import utc_now
from sqlalchemy import func, extract

logger = logging.getLogger(__name__)


class ExpenseNotFoundError(Exception):
    pass


class ExpensesService:
    def __init__(self):
        self.logger = logger
        self.categories_service = CategoriesService()

    async def create_expense(
        self, db: AsyncSession, expense_data: CreateExpenseModel
    ) -> None:
        """Create a new expense without returning any response"""
        self.logger.info(f"Creating new expense for user_id: {expense_data.user_id}")

        # Handle category and subcategory creation
        category_data = await self.categories_service.find_or_create_with_parent(
            db=db,
            category_name=expense_data.category_name or "",
            subcategory_name=expense_data.subcategory_name,
        )

        new_expense = Expense(
            user_id=expense_data.user_id,
            category_id=(
                category_data["category"].id if category_data["category"] else None
            ),
            amount=expense_data.amount,
            note=expense_data.note,
            source_message_id=expense_data.source_message_id,
        )

        db.add(new_expense)
        await db.commit()

        self.logger.info(f"Created expense for user_id: {expense_data.user_id}")

        return None

    async def delete_expense(self, db: AsyncSession, expense_id: int) -> None:
        """Soft delete an expense by setting deleted_at (no return)"""
        self.logger.info(f"Deleting expense with ID: {expense_id}")

        expense = await db.get(Expense, expense_id)
        if expense is None or expense.deleted_at is not None:
            self.logger.warning(
                f"Expense with ID {expense_id} not found or already deleted"
            )
            raise ExpenseNotFoundError(f"Expense {expense_id} not found")

        expense.deleted_at = utc_now()
        await db.commit()
        return None

    async def update_expense(
        self, db: AsyncSession, expense_id: int, update_data: Dict[str, Any]
    ) -> None:
        """Update an expense's details (no return)"""
        self.logger.info(f"Updating expense with ID: {expense_id}")

        expense = await db.get(Expense, expense_id)
        if expense is None or expense.deleted_at is not None:
            self.logger.warning(f"Expense with ID {expense_id} not found or deleted")
            raise ExpenseNotFoundError(f"Expense {expense_id} not found")

        for key, value in update_data.items():
            setattr(expense, key, value)

        await db.commit()
        return None

    async def get_all_expenses_for_user(
        self, db: AsyncSession, user_id: int
    ) -> Dict[str, list[Expense]]:
        """Retrieve all non-deleted expenses for a specific user"""
        self.logger.info(f"Fetching all expenses for user_id: {user_id}")

        query = select(Expense).where(
            Expense.user_id == user_id,
            Expense.deleted_at.is_(None),
        )
        result = await db.execute(query)
        return {"data": list(result.scalars().all())}

    async def get_expenses_by_category(
        self, db: AsyncSession, user_id: int, category_id: int
    ) -> Dict[str, list[Expense]]:
        """Retrieve non-deleted expenses filtered by category"""
        self.logger.info(
            f"Fetching expenses for user_id: {user_id} and category_id: {category_id}"
        )

        query = select(Expense).where(
            Expense.user_id == user_id,
            Expense.category_id == category_id,
            Expense.deleted_at.is_(None),
        )
        result = await db.execute(query)
        return {"data": list(result.scalars().all())}

    async def get_monthly_total(
        self,
        db: AsyncSession,
        user_id: int,
        month: Optional[int] = None,
        year: Optional[int] = None,
    ) -> Dict[Literal["total"], float]:
        """Get total expenses for a user for a given month and year (defaults to current month/year)"""
        """
        Returns:
            Dict[str, float]: {"total": float}
        """
        now = utc_now()
        month = month or now.month
        year = year or now.year

        query = select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.user_id == user_id,
            Expense.deleted_at.is_(None),
            extract("month", Expense.created_at) == month,
            extract("year", Expense.created_at) == year,
        )
        result = await db.execute(query)
        total = result.scalar_one()
        return {"total": total}

    async def demo_intent(self, text: str):
        """ """
        intent_classifier_agent = IntentClassifierAgent()
        intent_result = await intent_classifier_agent.classify(text)
        return intent_result
