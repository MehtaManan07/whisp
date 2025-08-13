from typing import TypedDict

from app.core.db import Category


class FindOrCreateResult(TypedDict):
    category: Category
    is_existing_category: bool
