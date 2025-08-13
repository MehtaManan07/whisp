import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, date
from decimal import Decimal

from agents.base_agent import BaseAgent
from app.agents.prompts.expense_prompts import EXPENSE_PROMPTS
from modules.users.models import User
from app.modules.expenses.service import ExpensesService, ExpenseNotFoundError
from app.modules.categories.service import CategoriesService

logger = logging.getLogger(__name__)


class ExpenseTrackerAgent(BaseAgent):
    """
    Specialized agent for handling expense-related operations.
    Handles adding, editing, deleting, and querying expenses.
    """

    def __init__(self, user: User):
        super().__init__("expense_tracker_agent", user)
        self.expense_service = ExpensesService()
        self.category_service = CategoriesService()
        # self.budget_service = BudgetService()

    def build_prompt(self, message: str) -> str:
        """
        Build expense-specific prompt with current spending context.
        """
        # Get base prompt from parent
        base_prompt = super().build_prompt(message)

        # Add expense-specific context
        expense_context = self._get_expense_context()

        # Get expense extraction prompt
        expense_instruction = EXPENSE_PROMPTS["extraction_prompt"]

        # Combine all parts
        full_prompt = f"{base_prompt}\n{expense_context}\n{expense_instruction}"

        return full_prompt

    def _get_expense_context(self) -> str:
        """
        Get current expense context for better processing.
        """
        try:
            # Get current month spending summary
            current_month_total = self.expense_service.get_monthly_total(
                user_id=self.user.id,
                month=datetime.now().month,
                year=datetime.now().year,
            )

            # Get recent categories used
            recent_categories = self.category_service.get_recent_categories(
                user_id=self.user.id, limit=10
            )

            category_list = (
                ", ".join([cat.name for cat in recent_categories])
                if recent_categories
                else "groceries, food, transport, entertainment"
            )

            return f"""
Current Context:
- This month's total spending: ₹{current_month_total}
- Your recent categories: {category_list}
- Today's date: {datetime.now().strftime('%Y-%m-%d')}
"""
        except Exception as e:
            logger.error(f"Error getting expense context: {e}")
            return "\nCurrent Context: Unable to load current spending data.\n"

    def validate_parsed_response(self, parsed_data: Dict[str, Any]) -> bool:
        """
        Validate expense-specific response structure.
        """
        if not isinstance(parsed_data, dict):
            return False

        action = parsed_data.get("action", "")

        # Validate based on action type
        if action == "add_expense":
            required_fields = ["amount", "category"]
            return all(field in parsed_data for field in required_fields)
        elif action == "edit_expense":
            return "expense_id" in parsed_data or "description" in parsed_data
        elif action == "delete_expense":
            return "expense_id" in parsed_data or "description" in parsed_data
        elif action == "get_expenses":
            return True  # No required fields for querying
        elif action == "categorize_expense":
            return "description" in parsed_data or "amount" in parsed_data

        return False

    def execute_action(self, parsed_response: Dict[str, Any]) -> str:
        """
        Execute expense-related actions based on parsed response.
        """
        if parsed_response["type"] == "text":
            # Return the LLM's text response
            return parsed_response["data"]["message"]

        try:
            data = parsed_response["data"]
            action = data.get("action", "")

            if action == "add_expense":
                return self._add_expense(data)
            elif action == "edit_expense":
                return self._edit_expense(data)
            elif action == "delete_expense":
                return self._delete_expense(data)
            elif action == "get_expenses":
                return self._get_expenses(data)
            elif action == "categorize_expense":
                return self._categorize_expense(data)
            else:
                return f"I understand you want to work with expenses, but I'm not sure how to handle: {action}"

        except Exception as e:
            logger.error(f"Error executing expense action: {e}")
            return "I encountered an error while processing your expense request. Please try again."

    def _add_expense(self, data: Dict[str, Any]) -> str:
        """
        Add a new expense.
        """
        try:
            # Extract and validate expense data
            amount = self._parse_amount(data.get("amount"))
            category_name = data.get("category", "").strip()
            description = data.get("description", "").strip()
            merchant = data.get("merchant", "").strip()
            expense_date = self._parse_date(data.get("date"))

            if not amount or amount <= 0:
                return "Please specify a valid amount for the expense."

            if not category_name:
                return "Please specify a category for the expense."

            # Get or create category
            category = self.category_service.get_or_create_category(
                user_id=self.user.id, category_name=category_name
            )

            # Create expense
            expense = self.expense_service.create_expense(
                user_id=self.user.id,
                category_id=category.id,
                amount=amount,
                description=description or f"{category_name} expense",
                merchant=merchant,
                expense_date=expense_date,
            )

            # Get budget status for this category
            budget_status = self._get_budget_status(category.id, amount)

            # Format success response
            response = f"✅ Added ₹{amount} {category_name} expense"

            if merchant:
                response += f" at {merchant}"

            if expense_date != date.today():
                response += f" for {expense_date.strftime('%Y-%m-%d')}"

            response += "."

            # Add budget status if available
            if budget_status:
                response += f"\n\n{budget_status}"

            return response

        except ValidationError as e:
            return f"Invalid expense data: {str(e)}"
        except DatabaseError as e:
            logger.error(f"Database error adding expense: {e}")
            return "I couldn't save your expense right now. Please try again."
        except Exception as e:
            logger.error(f"Unexpected error adding expense: {e}")
            return "I encountered an unexpected error while adding your expense."

    def _edit_expense(self, data: Dict[str, Any]) -> str:
        """
        Edit an existing expense.
        """
        try:
            # For V1, we'll implement basic editing by description/recent expense
            # More sophisticated editing can be added in V2

            description_search = data.get("description", "").strip()
            if not description_search:
                return "Please specify which expense you want to edit."

            # Find recent expense matching description
            recent_expense = self.expense_service.find_recent_expense_by_description(
                user_id=self.user.id,
                description=description_search,
                days_back=7,  # Look within last 7 days
            )

            if not recent_expense:
                return f"I couldn't find a recent expense matching '{description_search}'. Try being more specific."

            # Update fields if provided
            updates = {}
            if "amount" in data:
                updates["amount"] = self._parse_amount(data["amount"])
            if "category" in data:
                category = self.category_service.get_or_create_category(
                    user_id=self.user.id, category_name=data["category"]
                )
                updates["category_id"] = category.id
            if "merchant" in data:
                updates["merchant"] = data["merchant"]

            if not updates:
                return "Please specify what you want to change about the expense."

            # Update the expense
            updated_expense = self.expense_service.update_expense(
                expense_id=recent_expense.id, user_id=self.user.id, **updates
            )

            return f"✅ Updated expense: {updated_expense.description} - ₹{updated_expense.amount}"

        except Exception as e:
            logger.error(f"Error editing expense: {e}")
            return "I had trouble updating your expense. Please try again."

    def _delete_expense(self, data: Dict[str, Any]) -> str:
        """
        Delete an expense.
        """
        try:
            description_search = data.get("description", "").strip()
            if not description_search:
                return "Please specify which expense you want to delete."

            # Find recent expense matching description
            recent_expense = self.expense_service.find_recent_expense_by_description(
                user_id=self.user.id, description=description_search, days_back=7
            )

            if not recent_expense:
                return (
                    f"I couldn't find a recent expense matching '{description_search}'."
                )

            # Delete the expense
            self.expense_service.delete_expense(
                expense_id=recent_expense.id, user_id=self.user.id
            )

            return f"✅ Deleted expense: {recent_expense.description} - ₹{recent_expense.amount}"

        except Exception as e:
            logger.error(f"Error deleting expense: {e}")
            return "I had trouble deleting your expense. Please try again."

    def _get_expenses(self, data: Dict[str, Any]) -> str:
        """
        Get and display expenses based on criteria.
        """
        try:
            period = data.get("period", "recent").lower()
            category = data.get("category", "").strip()
            limit = data.get("limit", 10)

            if period == "today":
                expenses = self.expense_service.get_today_expenses(self.user.id)
                title = "Today's Expenses"
            elif period == "week":
                expenses = self.expense_service.get_weekly_expenses(self.user.id)
                title = "This Week's Expenses"
            elif period == "month":
                expenses = self.expense_service.get_monthly_expenses(self.user.id)
                title = "This Month's Expenses"
            else:
                expenses = self.expense_service.get_recent_expenses(self.user.id, limit)
                title = f"Recent Expenses (Last {limit})"

            # Filter by category if specified
            if category:
                expenses = [
                    exp
                    for exp in expenses
                    if category.lower() in exp.category.name.lower()
                ]
                title += f" - {category.title()}"

            if not expenses:
                return f"No expenses found for {title.lower()}."

            # Format expense list
            total = sum(expense.amount for expense in expenses)
            response = f"📊 **{title}**\n\n"

            for expense in expenses[:10]:  # Show max 10
                response += f"• ₹{expense.amount} - {expense.description}"
                if expense.merchant:
                    response += f" at {expense.merchant}"
                response += f" ({expense.expense_date.strftime('%m/%d')})\n"

            if len(expenses) > 10:
                response += f"... and {len(expenses) - 10} more\n"

            response += f"\n**Total: ₹{total}**"

            return response

        except Exception as e:
            logger.error(f"Error getting expenses: {e}")
            return "I had trouble retrieving your expenses. Please try again."

    def _categorize_expense(self, data: Dict[str, Any]) -> str:
        """
        Help categorize an expense or suggest categories.
        """
        description = data.get("description", "").strip()
        amount = data.get("amount")

        if not description:
            return "Please provide the expense description to help with categorization."

        # Get suggested category based on description
        suggested_category = self.category_service.suggest_category(
            user_id=self.user.id, description=description, amount=amount
        )

        # Get user's existing categories
        user_categories = self.category_service.get_user_categories(self.user.id)
        category_names = [cat.name for cat in user_categories]

        response = (
            f"💡 For '{description}', I suggest category: **{suggested_category}**\n\n"
        )

        if category_names:
            response += f"Your existing categories: {', '.join(category_names[:10])}"

        return response

    def _parse_amount(self, amount_input: Any) -> Optional[Decimal]:
        """
        Parse amount from various input formats.
        """
        if amount_input is None:
            return None

        try:
            # Remove currency symbols and spaces
            amount_str = str(amount_input).replace("₹", "").replace(",", "").strip()
            return Decimal(amount_str)
        except (ValueError, TypeError):
            return None

    def _parse_date(self, date_input: Any) -> date:
        """
        Parse date from input or return today.
        """
        if not date_input:
            return date.today()

        try:
            if isinstance(date_input, str):
                # Try common date formats
                for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
                    try:
                        return datetime.strptime(date_input, fmt).date()
                    except ValueError:
                        continue
            return date.today()
        except:
            return date.today()

    def _get_budget_status(
        self, category_id: str, expense_amount: Decimal
    ) -> Optional[str]:
        """
        Get budget status message for the category.
        """
        try:
            budget_status = self.budget_service.get_category_budget_status(
                user_id=self.user.id, category_id=category_id, current_month=True
            )

            if not budget_status:
                return None

            budget_limit = budget_status["limit"]
            current_spent = (
                budget_status["spent"] + expense_amount
            )  # Include this expense
            remaining = budget_limit - current_spent
            percentage_used = (current_spent / budget_limit) * 100

            if percentage_used >= 100:
                return f"⚠️ Budget Alert: You've exceeded your {budget_status['category_name']} budget by ₹{abs(remaining)}"
            elif percentage_used >= 80:
                return f"🟡 Budget Warning: {percentage_used:.0f}% of your {budget_status['category_name']} budget used (₹{remaining} remaining)"
            else:
                return f"📊 Budget Status: ₹{current_spent}/₹{budget_limit} used for {budget_status['category_name']} (₹{remaining} remaining)"

        except Exception as e:
            logger.error(f"Error getting budget status: {e}")
            return None
