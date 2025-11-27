from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.intelligence.intent.base_handler import BaseHandlers
from app.intelligence.intent.decorators import intent_handler
from app.intelligence.intent.types import (
    CLASSIFIED_RESULT,
    IntentType,
)
from app.modules.expenses.dto import CreateExpenseModel, GetAllExpensesModel
from app.modules.expenses.service import ExpensesService
from app.modules.users.service import UsersService
from app.modules.budgets.service import BudgetService
from app.modules.budgets.dto import ViewBudgetProgressDTO


class ExpenseHandlers(BaseHandlers):
    def __init__(self):
        super().__init__()
        self.service = ExpensesService()
        self.users_service = UsersService()
        self.budget_service = BudgetService()

    @intent_handler(IntentType.LOG_EXPENSE)
    async def log_expense(
        self, classified_result: CLASSIFIED_RESULT, user_id: int, db: AsyncSession
    ) -> str:
        """Handle log expense intent with timezone awareness."""
        dto_instance, intent = classified_result
        if not dto_instance:
            return "I couldn't understand the expense details. Please provide the amount and category (e.g., 'I spent ₹500 on groceries')."
        if not isinstance(dto_instance, CreateExpenseModel):
            return "Invalid data for creating expense."
        if not dto_instance.user_id:
            dto_instance.user_id = user_id
        
        # Get user timezone
        user = await self.users_service.get_user_by_id(db, user_id)
        user_timezone = self.users_service.get_user_timezone(user) if user else "UTC"
        
        await self.service.create_expense(db=db, data=dto_instance, user_timezone=user_timezone)
        
        # Create a meaningful confirmation message
        amount_str = f"₹{dto_instance.amount:,.2f}"
        category_info = ""
        
        if dto_instance.category_name and dto_instance.subcategory_name:
            category_info = f" under {dto_instance.category_name} > {dto_instance.subcategory_name}"
        elif dto_instance.category_name:
            category_info = f" under {dto_instance.category_name}"
        elif dto_instance.subcategory_name:
            category_info = f" under {dto_instance.subcategory_name}"
        
        vendor_info = f" at {dto_instance.vendor}" if dto_instance.vendor else ""
        note_info = f" (Note: {dto_instance.note})" if dto_instance.note else ""
        
        response = f"✅ Expense logged successfully!\n💰 Amount: {amount_str}{category_info}{vendor_info}{note_info}"
        
        # Check budget alerts
        budget_alerts = await self._check_budget_alerts(db, user_id, dto_instance.category_name, user_timezone)
        if budget_alerts:
            response += "\n\n" + budget_alerts
        
        return response

    @intent_handler(IntentType.VIEW_EXPENSES)
    async def view_expenses(
        self, classified_result: CLASSIFIED_RESULT, user_id: int, db: AsyncSession
    ) -> str:
        """Handle view expenses intent with timezone awareness."""
        dto_instance, intent = classified_result
        if not dto_instance:
            return "I couldn't understand what expenses you want to see. Please try again with more details."
        if not isinstance(dto_instance, GetAllExpensesModel):
            return "Invalid data for viewing expenses."
        if not dto_instance.user_id:
            dto_instance.user_id = user_id
        
        # Get user timezone
        user = await self.users_service.get_user_by_id(db, user_id)
        user_timezone = self.users_service.get_user_timezone(user) if user else "UTC"
        
        expenses = await self.service.get_expenses(db=db, data=dto_instance, user_timezone=user_timezone)
        
        # Handle case where no expenses found
        if not expenses:
            return "📊 No expenses found for your criteria. Either you're doing great with your spending, or we need to adjust the search filters!"
        
        # Handle aggregation results (single string value)
        if isinstance(expenses, str):
            agg_type = dto_instance.aggregation_type or "total"
            return f"📊 Your {agg_type} expense amount: ₹{expenses}"
        
        # Handle list of expenses
        if len(expenses) == 0:
            return "📊 No expenses found for your criteria. Either you're doing great with your spending, or we need to adjust the search filters!"
        
        # Format the response with a nice header
        expense_count = len(expenses)
        total_amount = sum(expense.amount for expense in expenses)
        
        response_parts = [
            f"📊 Found {expense_count} expense{'s' if expense_count != 1 else ''}",
            f"💰 Total amount: ₹{total_amount:,.2f}",
            "",
            "📝 Your expenses:"
        ]
        
        # Add each expense as a human-readable message (with timezone-aware times)
        for expense in expenses:
            response_parts.append(f"• {expense.to_human_message(user_timezone)}")
        
        return "\n".join(response_parts)

    async def _check_budget_alerts(
        self, db: AsyncSession, user_id: int, category_name: Optional[str], user_timezone: str
    ) -> str:
        """
        Check if any budget alerts should be triggered after logging an expense.
        Returns alert message if any thresholds are crossed, empty string otherwise.
        """
        try:
            # Check budgets for the specific category and overall budget
            progress_dto = ViewBudgetProgressDTO(
                user_id=user_id,
                category_name=category_name,
                period=None,
            )
            progress_list = await self.budget_service.get_budget_progress(
                db=db, data=progress_dto, user_timezone=user_timezone
            )
            
            # Also check overall budget (no category)
            overall_progress_dto = ViewBudgetProgressDTO(
                user_id=user_id,
                category_name=None,
                period=None,
            )
            overall_progress = await self.budget_service.get_budget_progress(
                db=db, data=overall_progress_dto, user_timezone=user_timezone
            )
            progress_list.extend(overall_progress)
            
            if not progress_list:
                return ""
            
            # Collect alerts that need to be shown
            alert_messages = []
            for progress in progress_list:
                if not progress.alerts_triggered:
                    continue
                
                budget = progress.budget
                category_info = f" for {budget.category_name}" if budget.category_name else ""
                
                # Determine alert level
                max_alert = max(progress.alerts_triggered)
                if max_alert >= 100:
                    emoji = "🔴"
                    status = "exceeded"
                elif max_alert >= 80:
                    emoji = "🟡"
                    status = "nearing limit"
                else:
                    continue  # Don't show alerts below 80%
                
                spent_str = f"₹{progress.spent:,.2f}"
                budget_str = f"₹{budget.amount:,.2f}"
                percentage_str = f"{progress.percentage:.1f}%"
                
                alert_messages.append(
                    f"{emoji} Budget Alert{category_info}: You've {status}! "
                    f"({percentage_str} - {spent_str} of {budget_str})"
                )
            
            if alert_messages:
                return "⚠️ Budget Alerts:\n" + "\n".join(alert_messages)
            
            return ""
            
        except Exception as e:
            # Don't fail expense logging if budget check fails
            import logging
            logging.getLogger(__name__).error(f"Error checking budget alerts: {str(e)}", exc_info=True)
            return ""
