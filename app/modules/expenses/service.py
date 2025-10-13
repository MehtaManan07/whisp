from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any
import dateparser

from app.core.db import Expense, Category
from app.core.exceptions import ExpenseNotFoundError, DatabaseError
from app.modules.expenses.dto import (
    CreateExpenseModel,
    DeleteExpenseModel,
    GetAllExpensesModel,
    ExpenseResponse,
)
from app.modules.categories.service import CategoriesService
import logging

from app.utils.datetime import utc_now
from sqlalchemy import func

logger = logging.getLogger(__name__)


class ExpensesService:
    def __init__(self):
        self.logger = logger
        self.categories_service = CategoriesService()

    async def get_expenses(
        self, db: AsyncSession, data: GetAllExpensesModel
    ) -> list[ExpenseResponse] | str:
        self.logger.debug(f"ExpensesService.get_expenses called with data: {data}")
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
            query = query.where(Expense.vendor == data.vendor.lower())
        if start_date:
            query = query.where(Expense.timestamp >= start_date)
        if end_date:
            query = query.where(Expense.timestamp <= end_date)
        if data.start_amount is not None:
            query = query.where(Expense.amount >= data.start_amount)
        if data.end_amount is not None:
            query = query.where(Expense.amount <= data.end_amount)
        if data.category_name and data.subcategory_name:
            # When both category and subcategory are specified, find expenses where
            # the category is the subcategory and its parent is the main category
            query = query.where(
                Expense.category.has(
                    (Category.name == data.subcategory_name)
                    & (Category.parent_id.isnot(None))
                    & (Category.parent.has(Category.name == data.category_name))
                )
            )
        elif data.category_name:
            query = query.where(
                Expense.category.has(
                    (Category.name == data.category_name)
                    & (Category.parent_id.is_(None))
                )
            )
        elif data.subcategory_name:
            query = query.where(
                Expense.category.has(
                    (Category.name == data.subcategory_name)
                    & (Category.parent_id.isnot(None))
                )
            )

        self.logger.debug(f"Executing query: {query}")
        result = await db.execute(query)

        if agg_func is None:
            expenses = result.scalars().all()
            return [
                ExpenseResponse(
                    **expense.__dict__,
                    category_name=expense.category.name if expense.category else None,
                )
                for expense in expenses
            ]
        else:
            # For aggregation functions, get the scalar result
            agg_result = result.scalar()
            return str(agg_result) if agg_result is not None else "0"

    async def create_expense(self, db: AsyncSession, data: CreateExpenseModel) -> None:
        """Create a new expense without returning any response"""
        self.logger.info(f"Creating new expense for user_id: {data.user_id}")

        try:
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
                vendor=data.vendor.lower() if data.vendor else None,
                timestamp=data.timestamp,
            )

            db.add(new_expense)
            await db.commit()

            self.logger.info(f"Created expense for user_id: {data.user_id}")
        except Exception as e:
            await db.rollback()
            self.logger.error(f"Database error during expense creation: {str(e)}")
            raise DatabaseError(f"create expense: {str(e)}")

        return None

    async def delete_expense(self, db: AsyncSession, data: DeleteExpenseModel) -> None:
        """Soft delete an expense by setting deleted_at (no return)"""
        self.logger.info(f"Deleting expense with ID: {data.id}")
        id = data.id

        try:
            expense = await db.scalar(
                select(Expense).where(Expense.id == id, Expense.deleted_at.is_(None))
            )
            if expense is None or expense.deleted_at is not None:
                self.logger.warning(
                    f"Expense with ID {id} not found or already deleted"
                )
                raise ExpenseNotFoundError(id)

            expense.deleted_at = utc_now()
            await db.commit()
        except Exception as e:
            await db.rollback()
            if isinstance(e, ExpenseNotFoundError):
                raise
            self.logger.error(f"Database error during expense deletion: {str(e)}")
            raise DatabaseError(f"delete expense: {str(e)}")

        return None

    async def update_expense(
        self, db: AsyncSession, expense_id: int, update_data: Dict[str, Any]
    ) -> None:
        """Update an expense's details (no return)"""
        self.logger.info(f"Updating expense with ID: {expense_id}")

        try:
            expense = await db.get(Expense, expense_id)
            if expense is None or expense.deleted_at is not None:
                self.logger.warning(
                    f"Expense with ID {expense_id} not found or deleted"
                )
                raise ExpenseNotFoundError(expense_id)

            for key, value in update_data.items():
                setattr(expense, key, value)

            await db.commit()
        except Exception as e:
            await db.rollback()
            if isinstance(e, ExpenseNotFoundError):
                raise
            self.logger.error(f"Database error during expense update: {str(e)}")
            raise DatabaseError(f"update expense: {str(e)}")

        return None
