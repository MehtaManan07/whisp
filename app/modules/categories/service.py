import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any

from app.infra.db import Category
from app.modules.categories.dto import CreateCategoryDto
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


# Global service instance
categories_service = CategoriesService()
