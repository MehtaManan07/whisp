from enum import Enum


class BudgetPeriod(str, Enum):
    """Enumeration of budget period types."""
    
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"

