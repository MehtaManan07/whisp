from app.intelligence.intent.base_handler import BaseHandlers
from app.intelligence.intent.decorators import intent_handler
from app.intelligence.intent.types import CLASSIFIED_RESULT, IntentType
from app.modules.budgets.dto import CreateBudgetModel, ViewBudgetsModel, DeleteBudgetModel
from app.modules.budgets.service import BudgetService
from app.modules.budgets.formatter import format_budget_list, format_budget_set_confirmation
from app.intelligence.categorization.constants import CATEGORIES

# Alias map: fuzzy input → parent category name
_CATEGORY_ALIASES = {
    "food": "Food & Dining",
    "food delivery": "Food & Dining",
    "restaurants": "Food & Dining",
    "dining": "Food & Dining",
    "groceries": "Food & Dining",
    "swiggy": "Food & Dining",
    "zomato": "Food & Dining",
    "transport": "Transportation",
    "transportation": "Transportation",
    "cab": "Transportation",
    "ride": "Transportation",
    "rapido": "Transportation",
    "uber": "Transportation",
    "ola": "Transportation",
    "shopping": "Shopping",
    "clothes": "Shopping",
    "amazon": "Shopping",
    "online shopping": "Shopping",
    "bills": "Bills & Utilities",
    "utilities": "Bills & Utilities",
    "rent": "Bills & Utilities",
    "electricity": "Bills & Utilities",
    "internet": "Bills & Utilities",
    "entertainment": "Entertainment",
    "movies": "Entertainment",
    "netflix": "Entertainment",
    "games": "Entertainment",
    "health": "Healthcare",
    "healthcare": "Healthcare",
    "doctor": "Healthcare",
    "medical": "Healthcare",
    "pharmacy": "Healthcare",
    "education": "Education",
    "courses": "Education",
    "books": "Education",
    "travel": "Travel",
    "hotel": "Travel",
    "flights": "Travel",
    "personal": "Personal Care",
    "personal care": "Personal Care",
    "salon": "Personal Care",
    "gym": "Personal Care",
    "grooming": "Personal Care",
    "business": "Business",
    "office": "Business",
    "professional": "Business",
    "investment": "Investments",
    "investments": "Investments",
    "stocks": "Investments",
    "mutual funds": "Investments",
    "gifts": "Gifts & Donations",
    "charity": "Gifts & Donations",
    "donations": "Gifts & Donations",
}


def _normalize_category(raw: str) -> str | None:
    """Normalize user input to a parent category name."""
    lowered = raw.strip().lower()

    # Direct match against CATEGORIES keys (case-insensitive)
    for cat_name in CATEGORIES:
        if lowered == cat_name.lower():
            return cat_name

    # Alias lookup
    if lowered in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[lowered]

    # Partial match: check if input is contained in any category name
    for cat_name in CATEGORIES:
        if lowered in cat_name.lower():
            return cat_name

    return None


class BudgetHandlers(BaseHandlers):
    def __init__(self):
        super().__init__()
        self.service = BudgetService()

    @intent_handler(IntentType.SET_BUDGET)
    async def set_budget(
        self, classified_result: CLASSIFIED_RESULT, user_id: int, user_timezone: str = "UTC"
    ) -> str:
        dto, _ = classified_result
        if not dto or not isinstance(dto, CreateBudgetModel):
            return "I couldn't understand your budget. Try: \"max 5000 on food per month\""

        dto.user_id = user_id

        # Normalize category
        normalized = _normalize_category(dto.category_name)
        if not normalized:
            available = ", ".join(CATEGORIES.keys())
            return f"I couldn't match \"{dto.category_name}\" to a category.\nAvailable: {available}"
        dto.category_name = normalized

        # Validate period
        if dto.period not in ("weekly", "monthly"):
            dto.period = "monthly"

        # Validate amount
        if dto.amount_limit <= 0:
            return "Budget amount must be greater than zero."

        result = await self.service.create_or_update_budget(dto)
        action = result["action"]

        msg = format_budget_set_confirmation(dto.category_name, dto.amount_limit, dto.period)
        if action == "updated":
            msg = msg.replace("Budget set:", "Budget updated:")

        return msg

    @intent_handler(IntentType.VIEW_BUDGETS)
    async def view_budgets(
        self, classified_result: CLASSIFIED_RESULT, user_id: int, user_timezone: str = "UTC"
    ) -> str:
        budgets = await self.service.get_budgets_with_status(user_id, user_timezone)
        return format_budget_list(budgets)

    @intent_handler(IntentType.DELETE_BUDGET)
    async def delete_budget(
        self, classified_result: CLASSIFIED_RESULT, user_id: int, user_timezone: str = "UTC"
    ) -> str:
        dto, _ = classified_result

        # Handle "delete all budgets"
        raw_category = ""
        if dto and isinstance(dto, DeleteBudgetModel):
            raw_category = dto.category_name.strip().lower()

        if raw_category in ("all", "everything", "all budgets", "") or not dto:
            count = await self.service.delete_all_budgets(user_id)
            if count:
                return f"✅ Removed all {count} budget{'s' if count != 1 else ''}. No more warnings."
            return "You don't have any active budgets."

        normalized = _normalize_category(raw_category)
        if not normalized:
            return f"I couldn't match \"{raw_category}\" to a category."

        deleted = await self.service.delete_budget(user_id, normalized)
        if deleted:
            return f"✅ Budget for *{normalized}* removed. No more warnings for this category."
        return f"No active budget found for *{normalized}*."
