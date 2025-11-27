from sqlalchemy.ext.asyncio import AsyncSession
from app.intelligence.intent.base_handler import BaseHandlers
from app.intelligence.intent.decorators import intent_handler
from app.intelligence.intent.types import CLASSIFIED_RESULT, IntentType
from app.modules.budgets.dto import (
    CreateBudgetDTO,
    GetBudgetDTO,
    ViewBudgetProgressDTO,
    UpdateBudgetDTO,
    DeleteBudgetDTO,
)
from app.modules.budgets.service import BudgetService
from app.modules.users.service import UsersService


class BudgetHandlers(BaseHandlers):
    def __init__(self):
        super().__init__()
        self.service = BudgetService()
        self.users_service = UsersService()

    @intent_handler(IntentType.SET_BUDGET)
    async def set_budget(
        self, classified_result: CLASSIFIED_RESULT, user_id: int, db: AsyncSession
    ) -> str:
        """Handle set budget intent."""
        dto_instance, intent = classified_result
        if not dto_instance:
            return "I couldn't understand the budget details. Please provide the amount and period (e.g., 'set monthly budget to 50000')."
        if not isinstance(dto_instance, CreateBudgetDTO):
            return "Invalid data for creating budget."
        if not dto_instance.user_id:
            dto_instance.user_id = user_id

        # Get user timezone
        user = await self.users_service.get_user_by_id(db, user_id)
        user_timezone = self.users_service.get_user_timezone(user) if user else "UTC"

        try:
            budget = await self.service.create_budget(
                db=db, data=dto_instance, user_timezone=user_timezone
            )

            # Create a meaningful confirmation message
            amount_str = f"₹{budget.amount:,.2f}"
            category_info = f" for {budget.category_name}" if budget.category_name else ""
            period_info = budget.period.value

            return f"✅ Budget created successfully!\n💰 Amount: {amount_str}\n📅 Period: {period_info}{category_info}\n🔔 Alerts at: {', '.join(str(int(t)) + '%' for t in budget.alert_thresholds)}"

        except Exception as e:
            return f"❌ Failed to create budget: {str(e)}"

    @intent_handler(IntentType.VIEW_BUDGET)
    async def view_budget(
        self, classified_result: CLASSIFIED_RESULT, user_id: int, db: AsyncSession
    ) -> str:
        """Handle view budget intent."""
        dto_instance, intent = classified_result
        if not dto_instance:
            return "I couldn't understand what budgets you want to see. Please try again."
        if not isinstance(dto_instance, GetBudgetDTO):
            return "Invalid data for viewing budgets."
        if not dto_instance.user_id:
            dto_instance.user_id = user_id

        try:
            budgets = await self.service.get_budgets(db=db, data=dto_instance)

            if not budgets:
                return "📊 No budgets found. Set one with 'set monthly budget to 50000' or 'set 5000 food budget'!"

            # Format the response
            budget_count = len(budgets)
            response_parts = [
                f"📊 Your Budgets ({budget_count}):",
                "",
            ]

            # Add each budget as a numbered item
            for idx, budget in enumerate(budgets, 1):
                status = "✅ Active" if budget.is_active else "⏸️ Inactive"
                category_info = f" - {budget.category_name}" if budget.category_name else " - Overall"
                amount_str = f"₹{budget.amount:,.2f}"

                response_parts.append(
                    f"{idx}. {budget.period.value.title()}{category_info}"
                )
                response_parts.append(f"   💰 {amount_str} | {status}")
                response_parts.append("")

            return "\n".join(response_parts)

        except Exception as e:
            return f"❌ Failed to retrieve budgets: {str(e)}"

    @intent_handler(IntentType.VIEW_BUDGET_PROGRESS)
    async def view_budget_progress(
        self, classified_result: CLASSIFIED_RESULT, user_id: int, db: AsyncSession
    ) -> str:
        """Handle view budget progress intent."""
        dto_instance, intent = classified_result
        if not dto_instance:
            return "I couldn't understand what budget progress you want to see. Please try again."
        if not isinstance(dto_instance, ViewBudgetProgressDTO):
            return "Invalid data for viewing budget progress."
        if not dto_instance.user_id:
            dto_instance.user_id = user_id

        # Get user timezone
        user = await self.users_service.get_user_by_id(db, user_id)
        user_timezone = self.users_service.get_user_timezone(user) if user else "UTC"

        try:
            progress_list = await self.service.get_budget_progress(
                db=db, data=dto_instance, user_timezone=user_timezone
            )

            if not progress_list:
                return "📊 No active budgets found. Set one with 'set monthly budget to 50000'!"

            # Format the response
            response_parts = [
                f"📊 Budget Progress ({len(progress_list)}):",
                "",
            ]

            # Add each budget progress
            for idx, progress in enumerate(progress_list, 1):
                budget = progress.budget
                category_info = f" - {budget.category_name}" if budget.category_name else " - Overall"
                
                # Determine status emoji
                if progress.percentage >= 100:
                    status_emoji = "🔴"
                    status_text = "Exceeded"
                elif progress.percentage >= 80:
                    status_emoji = "🟡"
                    status_text = "Near Limit"
                else:
                    status_emoji = "🟢"
                    status_text = "On Track"

                budget_str = f"₹{budget.amount:,.2f}"
                spent_str = f"₹{progress.spent:,.2f}"
                remaining_str = f"₹{progress.remaining:,.2f}"
                percentage_str = f"{progress.percentage:.1f}%"

                response_parts.append(
                    f"{idx}. {budget.period.value.title()}{category_info}"
                )
                response_parts.append(f"   {status_emoji} {status_text} - {percentage_str}")
                response_parts.append(f"   💰 Budget: {budget_str}")
                response_parts.append(f"   💸 Spent: {spent_str}")
                response_parts.append(f"   💵 Remaining: {remaining_str}")

                # Show alerts if triggered
                if progress.alerts_triggered:
                    alerts_str = ", ".join(f"{int(t)}%" for t in progress.alerts_triggered)
                    response_parts.append(f"   ⚠️ Alerts: {alerts_str}")

                response_parts.append("")

            return "\n".join(response_parts)

        except Exception as e:
            return f"❌ Failed to retrieve budget progress: {str(e)}"

    @intent_handler(IntentType.UPDATE_BUDGET)
    async def update_budget(
        self, classified_result: CLASSIFIED_RESULT, user_id: int, db: AsyncSession
    ) -> str:
        """Handle update budget intent."""
        dto_instance, intent = classified_result
        if not dto_instance:
            return "I couldn't understand which budget to update. Please specify the budget and what to change."
        if not isinstance(dto_instance, UpdateBudgetDTO):
            return "Invalid data for updating budget."

        try:
            budget = await self.service.update_budget(
                db=db, data=dto_instance, user_id=user_id
            )

            # Create a meaningful confirmation message
            amount_str = f"₹{budget.amount:,.2f}"
            category_info = f" for {budget.category_name}" if budget.category_name else ""
            period_info = budget.period.value

            return f"✅ Budget updated successfully!\n💰 Amount: {amount_str}\n📅 Period: {period_info}{category_info}"

        except Exception as e:
            return f"❌ Failed to update budget: {str(e)}"

    @intent_handler(IntentType.DELETE_BUDGET)
    async def delete_budget(
        self, classified_result: CLASSIFIED_RESULT, user_id: int, db: AsyncSession
    ) -> str:
        """Handle delete budget intent."""
        dto_instance, intent = classified_result
        if not dto_instance:
            return "I couldn't understand which budget to delete. Please specify the budget."
        if not isinstance(dto_instance, DeleteBudgetDTO):
            return "Invalid data for deleting budget."

        # Ensure user_id matches
        if not dto_instance.user_id:
            dto_instance.user_id = user_id
        elif dto_instance.user_id != user_id:
            return "❌ You can only delete your own budgets."

        try:
            success = await self.service.delete_budget(db=db, data=dto_instance)

            if success:
                return "✅ Budget deleted successfully!"
            else:
                return "❌ Failed to delete budget."

        except Exception as e:
            return f"❌ Failed to delete budget: {str(e)}"

