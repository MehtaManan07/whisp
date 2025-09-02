from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, Literal
import dateparser

from app.agents.intent_classifier.agent import IntentClassifierAgent
from app.core.db import Expense, Category
from app.modules.expenses.dto import (
    CreateExpenseModel,
    DeleteExpenseModel,
    ExpenseAggregationType,
    GetAllExpensesModel,
    ExpenseResponse,
)
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

    async def get_expenses(self, db: AsyncSession, data: GetAllExpensesModel):
        # Parse and validate dates only once
        start_date = dateparser.parse(data.start_date) if data.start_date else None
        end_date = dateparser.parse(data.end_date) if data.end_date else None

        if start_date and end_date and start_date >= end_date:
            end_date = start_date

        # Validate amount ranges
        if data.start_amount is not None and data.end_amount is not None:
            if data.start_amount >= data.end_amount:
                data.end_amount = data.start_amount

        field_map = {
            "sum": func.sum(Expense.amount),
            "count": func.count(),
            "avg": func.avg(Expense.amount),
            "min": func.min(Expense.amount),
            "max": func.max(Expense.amount),
        }

        agg_func = (
            field_map.get(data.aggregation_type) if data.aggregation_type else None
        )
        query = select(Expense if agg_func is None else agg_func).where(
            Expense.user_id == data.user_id
        )

        if data.vendor:
            query = query.where(Expense.vendor == data.vendor)
        if start_date:
            query = query.where(Expense.timestamp >= start_date)
        if end_date:
            query = query.where(Expense.timestamp <= end_date)
        if data.start_amount is not None:
            query = query.where(Expense.amount >= data.start_amount)
        if data.end_amount is not None:
            query = query.where(Expense.amount <= data.end_amount)
        if data.category_name:
            query = query.where(
                Expense.category.has(
                    (Category.name == data.category_name)
                    & (Category.parent_id.is_(None))
                )
            )
        if data.subcategory_name:
            query = query.where(
                Expense.category.has(
                    (Category.name == data.subcategory_name)
                    & (Category.parent_id.isnot(None))
                )
            )

        expenses = await db.execute(query)
        expenses = expenses.scalars().all()
        return [
            ExpenseResponse(
                **expense.__dict__,
                category_name=expense.category.name if expense.category else None,
            ).to_human_message()
            for expense in expenses
        ] if agg_func is None else expenses

    async def create_expense(self, db: AsyncSession, data: CreateExpenseModel) -> None:
        """Create a new expense without returning any response"""
        self.logger.info(f"Creating new expense for user_id: {data.user_id}")

        # Handle category and subcategory creation
        category_data = await self.categories_service.find_or_create_with_parent(
            db=db,
            category_name=data.category_name or "",
            subcategory_name=data.subcategory_name,
        )

        new_expense = Expense(
            user_id=data.user_id,
            category_id=(
                category_data["category"].id if category_data["category"] else None
            ),
            amount=data.amount,
            note=data.note,
            source_message_id=data.source_message_id,
            vendor=data.vendor,
            timestamp=data.timestamp,
        )

        db.add(new_expense)
        await db.commit()

        self.logger.info(f"Created expense for user_id: {data.user_id}")

        return None

    async def delete_expense(self, db: AsyncSession, data: DeleteExpenseModel) -> None:
        """Soft delete an expense by setting deleted_at (no return)"""
        self.logger.info(f"Deleting expense with ID: {data.id}")
        id = data.id

        expense = await db.scalar(
            select(Expense).where(Expense.id == id, Expense.deleted_at.is_(None))
        )
        if expense is None or expense.deleted_at is not None:
            self.logger.warning(f"Expense with ID {id} not found or already deleted")
            raise ExpenseNotFoundError(f"Expense {id} not found")

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

    async def demo_intent(self, db: AsyncSession, text: str):
        from app.agents.intent_classifier import route_intent

        """ """
        intent_classifier_agent = IntentClassifierAgent()
        intent_result = await intent_classifier_agent.classify(text)
        response = await route_intent(intent_result=intent_result, user_id=2, db=db)
        return intent_result
