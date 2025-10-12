# Import all models here to ensure they're loaded together
# This prevents circular import issues with relationships

from app.core.db.base import Base, BaseModel
from app.modules.users.models import User
from app.modules.categories.models import Category
from app.modules.expenses.models import Expense
from app.modules.reminders.models import Reminder

# Export for easy importing
__all__ = ["Base", "BaseModel", "User", "Category", "Expense", "Reminder"]
