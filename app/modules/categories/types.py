from typing import TypedDict

from app.modules.categories.models import Category


class FindOrCreateResult(TypedDict):
    category: Category
    is_existing_category: bool
