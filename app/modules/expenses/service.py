from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Dict, Any
import dateparser

from app.modules.expenses.models import Expense
from app.modules.categories.models import Category
from app.core.exceptions import ExpenseNotFoundError, DatabaseError
from app.modules.expenses.dto import (
    CreateExpenseModel,
    DeleteExpenseModel,
    GetAllExpensesModel,
    ExpenseResponse,
)
from app.modules.categories.service import CategoriesService
import logging

from app.utils.datetime import utc_now, to_utc
from sqlalchemy import func
from app.core.db.engine import run_db

logger = logging.getLogger(__name__)


class ExpensesService:
    def __init__(self):
        self.logger = logger
        self.categories_service = CategoriesService()

    async def get_expenses(
        self, data: GetAllExpensesModel, user_timezone: str = "UTC"
    ) -> list[ExpenseResponse] | str:
        """Get expenses with timezone-aware date parsing."""
        def _get(db: Session):
            start_date = None
            end_date = None

            if data.start_date:
                parsed = dateparser.parse(data.start_date, settings={'TIMEZONE': user_timezone, 'RETURN_AS_TIMEZONE_AWARE': True})
                if parsed:
                    start_date = parsed.astimezone(utc_now().tzinfo)

            if data.end_date:
                parsed = dateparser.parse(data.end_date, settings={'TIMEZONE': user_timezone, 'RETURN_AS_TIMEZONE_AWARE': True})
                if parsed:
                    end_date = parsed.astimezone(utc_now().tzinfo)

            if start_date and end_date and start_date >= end_date:
                end_date = start_date

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
            if data.note:
                query = query.where(Expense.note.ilike(f"%{data.note}%"))
            if start_date:
                query = query.where(Expense.timestamp >= start_date)
            if end_date:
                query = query.where(Expense.timestamp <= end_date)
            if data.start_amount is not None:
                query = query.where(Expense.amount >= data.start_amount)
            if data.end_amount is not None:
                query = query.where(Expense.amount <= data.end_amount)
            if data.category_name and data.subcategory_name:
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

            if agg_func is None:
                query = query.options(selectinload(Expense.category))

            result = db.execute(query)

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
                agg_result = result.scalar()
                return str(agg_result) if agg_result is not None else "0"

        return await run_db(_get)

    async def create_expense(self, data: CreateExpenseModel, user_timezone: str = "UTC") -> None:
        """Create a new expense with timezone-aware timestamp handling."""
        def _create(db: Session) -> None:
            try:
                category_data = self.categories_service.find_or_create_with_parent_sync(
                    db=db,
                    category_name=data.category_name or "",
                    subcategory_name=data.subcategory_name,
                )

                timestamp = data.timestamp
                if timestamp and timestamp.tzinfo is None:
                    timestamp = to_utc(timestamp, user_timezone)
                elif timestamp is None:
                    timestamp = utc_now()

                new_expense = Expense(
                    user_id=data.user_id,
                    category_id=(
                        category_data["category"].id if category_data["category"] else None
                    ),
                    amount=data.amount,
                    note=data.note,
                    source_message_id=data.source_message_id,
                    vendor=data.vendor.lower() if data.vendor else None,
                    timestamp=timestamp,
                    created_at=utc_now(),
                )

                db.add(new_expense)
                db.commit()
                logger.info(
                    "Expense created: user_id=%s amount=%.2f category_id=%s vendor=%s",
                    data.user_id,
                    data.amount,
                    new_expense.category_id,
                    new_expense.vendor,
                )
            except Exception as e:
                db.rollback()
                logger.error(f"Database error during expense creation: {str(e)}")
                raise DatabaseError(f"create expense: {str(e)}")

        await run_db(_create)

    async def delete_expense(self, data: DeleteExpenseModel) -> None:
        """Soft delete an expense by setting deleted_at."""
        def _delete(db: Session) -> None:
            try:
                expense = db.scalar(
                    select(Expense).where(Expense.id == data.id, Expense.deleted_at.is_(None))
                )
                if expense is None or expense.deleted_at is not None:
                    logger.warning(f"Expense with ID {data.id} not found or already deleted")
                    raise ExpenseNotFoundError(data.id)

                expense.deleted_at = utc_now()
                db.commit()
            except Exception as e:
                db.rollback()
                if isinstance(e, ExpenseNotFoundError):
                    raise
                logger.error(f"Database error during expense deletion: {str(e)}")
                raise DatabaseError(f"delete expense: {str(e)}")

        await run_db(_delete)

    async def update_expense(
        self, expense_id: int, update_data: Dict[str, Any]
    ) -> None:
        """Update an expense's details."""
        def _update(db: Session) -> None:
            try:
                expense = db.get(Expense, expense_id)
                if expense is None or expense.deleted_at is not None:
                    logger.warning(f"Expense with ID {expense_id} not found or deleted")
                    raise ExpenseNotFoundError(expense_id)

                for key, value in update_data.items():
                    setattr(expense, key, value)

                db.commit()
            except Exception as e:
                db.rollback()
                if isinstance(e, ExpenseNotFoundError):
                    raise
                logger.error(f"Database error during expense update: {str(e)}")
                raise DatabaseError(f"update expense: {str(e)}")

        await run_db(_update)

    async def get_latest_expense(
        self, user_id: int
    ) -> Expense | None:
        """Get the most recently created expense for a user."""
        def _get(db: Session) -> Expense | None:
            try:
                result = db.execute(
                    select(Expense)
                    .options(selectinload(Expense.category))
                    .where(Expense.user_id == user_id)
                    .where(Expense.deleted_at.is_(None))
                    .order_by(Expense.created_at.desc())
                    .limit(1)
                )
                return result.scalar_one_or_none()
            except Exception as e:
                logger.error(f"Error getting latest expense: {str(e)}")
                return None

        return await run_db(_get)

    async def update_expense_category(
        self,
        expense_id: int,
        category_name: str,
        subcategory_name: str | None = None,
    ) -> Expense:
        """Update an expense's category and subcategory."""
        def _update(db: Session) -> Expense:
            try:
                expense = db.get(Expense, expense_id)
                if expense is None or expense.deleted_at is not None:
                    raise ExpenseNotFoundError(expense_id)

                category = self.categories_service.find_or_create_category_sync(
                    db=db,
                    category_name=category_name,
                    subcategory_name=subcategory_name,
                )

                expense.category_id = category.id
                db.commit()
                db.refresh(expense)

                return expense
            except Exception as e:
                db.rollback()
                if isinstance(e, ExpenseNotFoundError):
                    raise
                logger.error(f"Error updating expense category: {str(e)}")
                raise DatabaseError(f"update expense category: {str(e)}")

        return await run_db(_update)
