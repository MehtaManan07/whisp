from typing import Any, Dict, Optional
from app.intelligence.intent.base_handler import BaseHandlers
from app.intelligence.intent.decorators import intent_handler
from app.intelligence.intent.types import (
    CLASSIFIED_RESULT,
    IntentType,
)
from app.modules.expenses.dto import CreateExpenseModel, GetAllExpensesModel, CorrectExpenseModel
from app.modules.expenses.service import ExpensesService
from app.intelligence.categorization.constants import CATEGORIES, is_valid_category


class ExpenseHandlers(BaseHandlers):
    def __init__(self):
        super().__init__()
        self.service = ExpensesService()

    @intent_handler(IntentType.LOG_EXPENSE)
    async def log_expense(
        self, classified_result: CLASSIFIED_RESULT, user_id: int, user_timezone: str = "UTC"
    ) -> str:
        """Handle log expense intent with timezone awareness."""
        dto_instance, intent = classified_result
        if not dto_instance:
            return "I couldn't understand the expense details. Please provide the amount and category (e.g., 'I spent ₹500 on groceries')."
        if not isinstance(dto_instance, CreateExpenseModel):
            return "Invalid data for creating expense."
        if not dto_instance.user_id:
            dto_instance.user_id = user_id

        await self.service.create_expense(data=dto_instance, user_timezone=user_timezone)

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

        confidence = getattr(dto_instance, 'classification_confidence', None)
        if confidence is not None and confidence < 0.7:
            response += f"\n\n⚠️ I'm not 100% sure about this category (confidence: {confidence:.0%}). Reply with the correct category if needed."

        return response

    @intent_handler(IntentType.VIEW_EXPENSES)
    async def view_expenses(
        self, classified_result: CLASSIFIED_RESULT, user_id: int, user_timezone: str = "UTC"
    ) -> str:
        """Handle view expenses intent with timezone awareness."""
        dto_instance, intent = classified_result
        if not dto_instance:
            return "I couldn't understand what expenses you want to see. Please try again with more details."
        if not isinstance(dto_instance, GetAllExpensesModel):
            return "Invalid data for viewing expenses."
        if not dto_instance.user_id:
            dto_instance.user_id = user_id

        expenses = await self.service.get_expenses(data=dto_instance, user_timezone=user_timezone)

        if not expenses:
            return "📊 No expenses found for your criteria. Either you're doing great with your spending, or we need to adjust the search filters!"

        if isinstance(expenses, str):
            agg_type = dto_instance.aggregation_type or "total"
            return f"📊 Your {agg_type} expense amount: ₹{expenses}"

        if len(expenses) == 0:
            return "📊 No expenses found for your criteria. Either you're doing great with your spending, or we need to adjust the search filters!"

        expense_count = len(expenses)
        total_amount = sum(expense.amount for expense in expenses)

        response_parts = [
            f"📊 Found {expense_count} expense{'s' if expense_count != 1 else ''}",
            f"💰 Total amount: ₹{total_amount:,.2f}",
            "",
            "📝 Your expenses:"
        ]

        for expense in expenses:
            response_parts.append(f"• {expense.to_human_message(user_timezone)}")

        return "\n".join(response_parts)

    @intent_handler(IntentType.CORRECT_EXPENSE)
    async def correct_expense(
        self, classified_result: CLASSIFIED_RESULT, user_id: int, user_timezone: str = "UTC"
    ) -> str:
        """Handle expense category correction."""
        dto_instance, intent = classified_result
        if not dto_instance:
            return "I couldn't understand the correction. Please specify the correct category (e.g., 'change category to Business')."
        if not isinstance(dto_instance, CorrectExpenseModel):
            return "Invalid data for correcting expense."
        if not dto_instance.user_id:
            dto_instance.user_id = user_id

        category = dto_instance.correct_category
        subcategory = dto_instance.correct_subcategory

        if category not in CATEGORIES:
            available = ", ".join(CATEGORIES.keys())
            return f"'{category}' is not a valid category. Available categories: {available}"

        if subcategory and not is_valid_category(category, subcategory):
            available = ", ".join(CATEGORIES[category])
            return f"'{subcategory}' is not a valid subcategory for {category}. Available: {available}"

        if dto_instance.expense_id:
            expense_id = dto_instance.expense_id
        else:
            latest_expense = await self.service.get_latest_expense(user_id)
            if not latest_expense:
                return "No recent expense found to correct. Please specify which expense to correct."
            expense_id = latest_expense.id

        try:
            expense = await self.service.get_latest_expense(user_id)
            old_category = None
            old_subcategory = None

            if expense and expense.id == expense_id:
                if expense.category:
                    old_category = expense.category.name
                    if expense.category.parent:
                        old_category = expense.category.parent.name
                        old_subcategory = expense.category.name

            if not subcategory:
                subcategory = CATEGORIES[category][0]

            await self.service.update_expense_category(
                expense_id=expense_id,
                category_name=category,
                subcategory_name=subcategory,
            )

            response = f"✅ Category updated to {category} > {subcategory}"

            if old_category:
                response += f"\n📝 Changed from: {old_category}"
                if old_subcategory:
                    response += f" > {old_subcategory}"

            return response

        except Exception as e:
            return f"Failed to update category: {str(e)}"
