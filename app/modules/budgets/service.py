import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ValidationError, DatabaseError
from app.modules.budgets.models import Budget
from app.modules.budgets.dto import (
    CreateBudgetDTO,
    UpdateBudgetDTO,
    GetBudgetDTO,
    ViewBudgetProgressDTO,
    DeleteBudgetDTO,
    BudgetResponseDTO,
    BudgetProgressResponseDTO,
)
from app.modules.budgets.types import BudgetPeriod
from app.modules.categories.models import Category
from app.modules.expenses.models import Expense
from app.utils.datetime import utc_now

logger = logging.getLogger(__name__)


class BudgetService:
    """Service for managing budgets."""

    async def create_budget(
        self, db: AsyncSession, data: CreateBudgetDTO, user_timezone: str = "UTC"
    ) -> BudgetResponseDTO:
        """Create a new budget."""
        try:
            # Look up category if provided
            category_id = None
            category_name = None
            if data.category_name:
                category = await self._get_category_by_name(db, data.category_name)
                if category:
                    category_id = category.id
                    category_name = category.name
                else:
                    raise ValidationError(f"Category '{data.category_name}' not found")

            # Check if similar budget already exists
            existing = await self._check_existing_budget(
                db, data.user_id, category_id, data.period
            )
            if existing:
                raise ValidationError(
                    f"A budget for this period and category already exists (ID: {existing.id})"
                )

            # Create the budget
            budget = Budget(
                user_id=data.user_id,
                category_id=category_id,
                period=data.period,
                amount=data.amount,
                alert_thresholds=data.alert_thresholds,
                is_active=True,
            )

            db.add(budget)
            await db.commit()
            await db.refresh(budget)

            logger.info(
                f"Created budget {budget.id} for user {data.user_id}: {data.period} - {data.amount}"
            )

            return self._to_response_dto(budget, category_name)

        except ValidationError:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating budget: {str(e)}", exc_info=True)
            raise DatabaseError(f"Failed to create budget: {str(e)}")

    async def get_budgets(
        self, db: AsyncSession, data: GetBudgetDTO
    ) -> List[BudgetResponseDTO]:
        """Get budgets with optional filters."""
        try:
            query = select(Budget).where(Budget.user_id == data.user_id)

            # Apply filters
            if data.is_active is not None:
                query = query.where(Budget.is_active == data.is_active)

            if data.period:
                query = query.where(Budget.period == data.period)

            if data.category_name:
                category = await self._get_category_by_name(db, data.category_name)
                if category:
                    query = query.where(Budget.category_id == category.id)
                else:
                    return []  # Category not found, return empty list

            # Filter out soft-deleted budgets
            query = query.where(Budget.deleted_at.is_(None))

            result = await db.execute(query)
            budgets = result.scalars().all()

            # Convert to response DTOs with category names
            response_dtos = []
            for budget in budgets:
                category_name = None
                if budget.category_id:
                    category = await self._get_category_by_id(db, budget.category_id)
                    if category:
                        category_name = category.name
                response_dtos.append(self._to_response_dto(budget, category_name))

            return response_dtos

        except Exception as e:
            logger.error(f"Error getting budgets: {str(e)}", exc_info=True)
            raise DatabaseError(f"Failed to get budgets: {str(e)}")

    async def get_budget_by_id(
        self, db: AsyncSession, budget_id: int
    ) -> Optional[BudgetResponseDTO]:
        """Get a single budget by ID."""
        try:
            query = select(Budget).where(
                and_(Budget.id == budget_id, Budget.deleted_at.is_(None))
            )
            result = await db.execute(query)
            budget = result.scalar_one_or_none()

            if not budget:
                return None

            category_name = None
            if budget.category_id:
                category = await self._get_category_by_id(db, budget.category_id)
                if category:
                    category_name = category.name

            return self._to_response_dto(budget, category_name)

        except Exception as e:
            logger.error(f"Error getting budget by ID: {str(e)}", exc_info=True)
            raise DatabaseError(f"Failed to get budget: {str(e)}")

    async def get_budget_progress(
        self, db: AsyncSession, data: ViewBudgetProgressDTO, user_timezone: str = "UTC"
    ) -> List[BudgetProgressResponseDTO]:
        """Calculate spending vs budget for the given period."""
        try:
            # Get matching budgets
            get_dto = GetBudgetDTO(
                user_id=data.user_id,
                category_name=data.category_name,
                period=data.period,
                is_active=True,
            )
            budgets = await self.get_budgets(db, get_dto)

            if not budgets:
                return []

            # Calculate progress for each budget
            progress_list = []
            for budget_dto in budgets:
                # Calculate period dates
                period_start, period_end = self.calculate_period_dates(
                    budget_dto.period, user_timezone
                )

                # Get spending for this budget's period and category
                spent = await self._get_spending_for_period(
                    db,
                    data.user_id,
                    budget_dto.category_id,
                    period_start,
                    period_end,
                )

                # Calculate remaining and percentage
                remaining = budget_dto.amount - spent
                percentage = (spent / budget_dto.amount * 100) if budget_dto.amount > 0 else 0

                # Check which alerts have been triggered
                alerts_triggered = [
                    threshold
                    for threshold in budget_dto.alert_thresholds
                    if percentage >= threshold
                ]

                progress = BudgetProgressResponseDTO(
                    budget=budget_dto,
                    spent=spent,
                    remaining=remaining,
                    percentage=round(percentage, 2),
                    alerts_triggered=alerts_triggered,
                    period_start=period_start,
                    period_end=period_end,
                )
                progress_list.append(progress)

            return progress_list

        except Exception as e:
            logger.error(f"Error getting budget progress: {str(e)}", exc_info=True)
            raise DatabaseError(f"Failed to get budget progress: {str(e)}")

    async def update_budget(
        self, db: AsyncSession, data: UpdateBudgetDTO, user_id: int
    ) -> BudgetResponseDTO:
        """Update an existing budget."""
        try:
            # Get the budget
            query = select(Budget).where(
                and_(
                    Budget.id == data.budget_id,
                    Budget.user_id == user_id,
                    Budget.deleted_at.is_(None),
                )
            )
            result = await db.execute(query)
            budget = result.scalar_one_or_none()

            if not budget:
                raise ValidationError("Budget not found or access denied")

            # Update fields if provided
            if data.amount is not None:
                budget.amount = data.amount

            if data.period is not None:
                budget.period = data.period

            if data.category_name is not None:
                category = await self._get_category_by_name(db, data.category_name)
                if category:
                    budget.category_id = category.id
                else:
                    raise ValidationError(f"Category '{data.category_name}' not found")

            if data.alert_thresholds is not None:
                budget.alert_thresholds = data.alert_thresholds

            if data.is_active is not None:
                budget.is_active = data.is_active

            budget.updated_at = utc_now()

            await db.commit()
            await db.refresh(budget)

            logger.info(f"Updated budget {budget.id} for user {user_id}")

            category_name = None
            if budget.category_id:
                category = await self._get_category_by_id(db, budget.category_id)
                if category:
                    category_name = category.name

            return self._to_response_dto(budget, category_name)

        except ValidationError:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating budget: {str(e)}", exc_info=True)
            raise DatabaseError(f"Failed to update budget: {str(e)}")

    async def delete_budget(
        self, db: AsyncSession, data: DeleteBudgetDTO
    ) -> bool:
        """Soft delete a budget."""
        try:
            # Get the budget
            query = select(Budget).where(
                and_(
                    Budget.id == data.budget_id,
                    Budget.user_id == data.user_id,
                    Budget.deleted_at.is_(None),
                )
            )
            result = await db.execute(query)
            budget = result.scalar_one_or_none()

            if not budget:
                raise ValidationError("Budget not found or access denied")

            # Soft delete
            budget.deleted_at = utc_now()
            await db.commit()

            logger.info(f"Deleted budget {budget.id} for user {data.user_id}")
            return True

        except ValidationError:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting budget: {str(e)}", exc_info=True)
            raise DatabaseError(f"Failed to delete budget: {str(e)}")

    def check_budget_alerts(
        self, budget_amount: float, spent: float, alert_thresholds: List[float]
    ) -> List[float]:
        """Determine if any alert thresholds have been crossed."""
        percentage = (spent / budget_amount * 100) if budget_amount > 0 else 0
        return [
            threshold for threshold in alert_thresholds if percentage >= threshold
        ]

    def calculate_period_dates(
        self, period: BudgetPeriod, user_timezone: str = "UTC"
    ) -> Tuple[datetime, datetime]:
        """
        Calculate the start and end dates for a budget period.
        Returns rolling periods (e.g., monthly = last 30 days from now).
        """
        from app.utils.datetime import to_user_timezone

        now = to_user_timezone(utc_now(), user_timezone)

        if period == BudgetPeriod.DAILY:
            # Start of today to end of today
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        elif period == BudgetPeriod.WEEKLY:
            # Last 7 days
            start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        elif period == BudgetPeriod.MONTHLY:
            # Last 30 days
            start = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        elif period == BudgetPeriod.YEARLY:
            # Last 365 days
            start = (now - timedelta(days=365)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        else:
            raise ValueError(f"Invalid budget period: {period}")

        return start, end

    # Helper methods
    # ============================================================================

    async def _get_category_by_name(
        self, db: AsyncSession, name: str
    ) -> Optional[Category]:
        """Get category by name (case-insensitive)."""
        query = select(Category).where(
            and_(
                func.lower(Category.name) == name.lower(),
                Category.deleted_at.is_(None),
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _get_category_by_id(
        self, db: AsyncSession, category_id: int
    ) -> Optional[Category]:
        """Get category by ID."""
        query = select(Category).where(
            and_(Category.id == category_id, Category.deleted_at.is_(None))
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _check_existing_budget(
        self,
        db: AsyncSession,
        user_id: int,
        category_id: Optional[int],
        period: BudgetPeriod,
    ) -> Optional[Budget]:
        """Check if a similar budget already exists."""
        query = select(Budget).where(
            and_(
                Budget.user_id == user_id,
                Budget.category_id == category_id,
                Budget.period == period,
                Budget.deleted_at.is_(None),
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _get_spending_for_period(
        self,
        db: AsyncSession,
        user_id: int,
        category_id: Optional[int],
        start_date: datetime,
        end_date: datetime,
    ) -> float:
        """Calculate total spending for a user in a given period and category."""
        query = select(func.sum(Expense.amount)).where(
            and_(
                Expense.user_id == user_id,
                Expense.timestamp >= start_date,
                Expense.timestamp <= end_date,
                Expense.deleted_at.is_(None),
            )
        )

        # If category_id is provided, filter by it
        if category_id is not None:
            query = query.where(Expense.category_id == category_id)

        result = await db.execute(query)
        total = result.scalar()

        return float(total) if total else 0.0

    def _to_response_dto(
        self, budget: Budget, category_name: Optional[str] = None
    ) -> BudgetResponseDTO:
        """Convert Budget model to BudgetResponseDTO."""
        return BudgetResponseDTO(
            id=budget.id,
            user_id=budget.user_id,
            category_id=budget.category_id,
            category_name=category_name,
            period=budget.period,
            amount=budget.amount,
            alert_thresholds=budget.alert_thresholds,
            is_active=budget.is_active,
            created_at=budget.created_at,
            updated_at=budget.updated_at,
        )

