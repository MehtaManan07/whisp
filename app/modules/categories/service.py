import logging
from typing_extensions import Literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Dict, Sequence

from app.infra.db import Category
from app.modules.categories.dto import CreateCategoryDto
from app.modules.categories.sql import GET_RECENT_CATEGORIES
from app.modules.categories.types import FindOrCreateResult

logger = logging.getLogger(__name__)


class CategoriesService:
    def __init__(self):
        self.logger = logger

    async def find_or_create(
        self, db: AsyncSession, category_data: CreateCategoryDto
    ) -> FindOrCreateResult:
        """Find existing category or create new one"""
        # Try to find existing category
        result = await db.execute(
            select(Category).where(Category.name == category_data.name)
        )
        category = result.scalar_one_or_none()

        if category:
            return {"category": category, "is_existing_category": True}

        # Create new category
        self.logger.info(f"Creating new category with name: {category_data.name}")

        new_category = Category(
            name=category_data.name,
            description=category_data.description,
        )

        db.add(new_category)
        await db.commit()
        await db.refresh(new_category)

        return {"category": new_category, "is_existing_category": False}

    # Get recent categories used
    async def get_recent_categories(
        self, db: AsyncSession, user_id: int, limit: int = 10
    ) -> Dict[Literal["categories"], Sequence[Category]]:
        """Fetch recent categories user by the user"""
        self.logger.info(
            f"Fetching recent categories for user_id: {user_id} with limit: {limit}"
        )

        sql = text(GET_RECENT_CATEGORIES)
        result = await db.execute(sql, {"user_id": user_id, "limit": limit})

        if result is None:
            return {"categories": []}

        categories = result.scalars().all()

        return {"categories": categories}
