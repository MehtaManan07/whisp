import logging
from typing_extensions import Literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Dict, Sequence, Optional, List
from sqlalchemy.orm import selectinload

from app.core.db import Category
from app.modules.categories.dto import (
    CreateCategoryDto,
    CategoryResponseDto,
    CategoryTreeDto,
)
from app.modules.categories.sql import (
    GET_RECENT_CATEGORIES,
    GET_CATEGORIES_WITH_USAGE_COUNT,
)
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
        query = select(Category).where(Category.name == category_data.name)

        # If looking for a subcategory, also match parent_id
        if category_data.parent_id:
            query = query.where(Category.parent_id == category_data.parent_id)
        else:
            query = query.where(Category.parent_id.is_(None))

        result = await db.execute(query)
        category = result.scalar_one_or_none()

        if category:
            return {"category": category, "is_existing_category": True}

        # Create new category
        self.logger.info(f"Creating new category with name: {category_data.name}")

        new_category = Category(
            name=category_data.name,
            description=category_data.description,
            parent_id=category_data.parent_id,
        )

        db.add(new_category)
        await db.commit()
        await db.refresh(new_category)

        return {"category": new_category, "is_existing_category": False}

    async def find_or_create_with_parent(
        self,
        db: AsyncSession,
        category_name: str,
        subcategory_name: Optional[str] = None,
    ) -> FindOrCreateResult:
        """Find or create category and subcategory if specified"""
        # First, find or create the parent category
        parent_result = await self.find_or_create(
            db, CreateCategoryDto(name=category_name)
        )
        parent_category = parent_result["category"]

        # If no subcategory specified, return the parent
        if not subcategory_name:
            return parent_result

        # Find or create the subcategory
        subcategory_result = await self.find_or_create(
            db, CreateCategoryDto(name=subcategory_name, parent_id=parent_category.id)
        )

        return subcategory_result

    async def get_category_tree(self, db: AsyncSession) -> List[CategoryTreeDto]:
        """Get all categories organized in a tree structure"""
        # Get all categories with their subcategories
        result = await db.execute(
            select(Category)
            .where(Category.parent_id.is_(None))
            .options(selectinload(Category.subcategories))
            .order_by(Category.name)
        )
        parent_categories = result.scalars().all()

        category_trees = []
        for category in parent_categories:
            subcategories = [
                CategoryTreeDto(
                    id=sub.id,
                    name=sub.name,
                    description=sub.description,
                    subcategories=[],
                )
                for sub in sorted(category.subcategories, key=lambda x: x.name)
            ]

            category_trees.append(
                CategoryTreeDto(
                    id=category.id,
                    name=category.name,
                    description=category.description,
                    subcategories=subcategories,
                )
            )

        return category_trees

    async def get_all_categories(self, db: AsyncSession) -> List[CategoryResponseDto]:
        """Get all categories as a flat list with hierarchy information"""
        result = await db.execute(
            select(Category)
            .options(selectinload(Category.parent))
            .order_by(Category.name)
        )
        categories = result.scalars().all()

        return [
            CategoryResponseDto(
                id=cat.id,
                name=cat.name,
                description=cat.description,
                parent_id=cat.parent_id,
                full_name=cat.full_name,
                is_subcategory=cat.is_subcategory,
            )
            for cat in categories
        ]

    # Get recent categories used
    async def get_recent_categories(
        self, db: AsyncSession, user_id: int, limit: int = 10
    ) -> Dict[Literal["categories"], Sequence[Category]]:
        """Fetch recent categories used by the user"""
        self.logger.info(
            f"Fetching recent categories for user_id: {user_id} with limit: {limit}"
        )

        sql = text(GET_RECENT_CATEGORIES)
        result = await db.execute(sql, {"user_id": user_id, "limit": limit})

        if result is None:
            return {"categories": []}

        categories = result.scalars().all()

        return {"categories": categories}

    async def get_categories_with_usage_count(
        self, db: AsyncSession, user_id: int
    ) -> List[Dict]:
        """Get categories with their usage count for the user"""
        self.logger.info(f"Fetching categories with usage count for user_id: {user_id}")

        sql = text(GET_CATEGORIES_WITH_USAGE_COUNT)
        result = await db.execute(sql, {"user_id": user_id})

        if result is None:
            return []

        rows = result.fetchall()
        return [
            {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "parent_id": row.parent_id,
                "parent_name": row.parent_name,
                "usage_count": row.usage_count,
                "full_name": (
                    f"{row.parent_name} > {row.name}" if row.parent_name else row.name
                ),
            }
            for row in rows
        ]
