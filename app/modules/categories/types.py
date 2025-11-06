from typing import TypedDict

from app.modules.categories.models import Category


class FindOrCreateResult(TypedDict):
    """Result of finding or creating a category."""
    category: Category  # The category object that was found or created
    is_existing_category: bool  # Whether the category already existed or was newly created
