import logging
from typing_extensions import Literal
from sqlalchemy.orm import Session
from sqlalchemy import select, text
from typing import Dict, Sequence, Optional, List
from sqlalchemy.orm import selectinload

from app.modules.categories.models import Category
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
from app.core.db.engine import run_db
from app.utils.datetime import utc_now

logger = logging.getLogger(__name__)


class CategoriesService:
    def __init__(self):
        self.logger = logger

    # -------------------------------------------------------------------------
    # Sync helpers (called from within run_db blocks in other services)
    # -------------------------------------------------------------------------

    def find_or_create_sync(
        self, db: Session, category_data: CreateCategoryDto
    ) -> FindOrCreateResult:
        """Find existing category or create new one (sync)."""
        query = select(Category).where(Category.name == category_data.name)

        if category_data.parent_id:
            query = query.where(Category.parent_id == category_data.parent_id)
        else:
            query = query.where(Category.parent_id.is_(None))

        result = db.execute(query)
        category = result.scalar_one_or_none()

        if category:
            return {"category": category, "is_existing_category": True}

        new_category = Category(
            name=category_data.name,
            description=category_data.description,
            parent_id=category_data.parent_id,
            created_at=utc_now(),
        )

        db.add(new_category)
        db.flush()
        db.refresh(new_category)

        return {"category": new_category, "is_existing_category": False}

    def find_or_create_with_parent_sync(
        self,
        db: Session,
        category_name: str,
        subcategory_name: Optional[str] = None,
    ) -> FindOrCreateResult:
        """Find or create category and subcategory if specified (sync)."""
        parent_result = self.find_or_create_sync(
            db, CreateCategoryDto(name=category_name)
        )
        parent_category = parent_result["category"]

        if not subcategory_name:
            return parent_result

        subcategory_result = self.find_or_create_sync(
            db, CreateCategoryDto(name=subcategory_name, parent_id=parent_category.id)
        )

        return subcategory_result

    def find_or_create_category_sync(
        self,
        db: Session,
        category_name: str,
        subcategory_name: Optional[str] = None,
    ) -> Category:
        """Find or create a category, returning the Category object (sync)."""
        result = self.find_or_create_with_parent_sync(db, category_name, subcategory_name)
        return result["category"]

    # -------------------------------------------------------------------------
    # Async public API (called from controllers / handlers)
    # -------------------------------------------------------------------------

    async def find_or_create(
        self, category_data: CreateCategoryDto
    ) -> FindOrCreateResult:
        return await run_db(lambda db: self.find_or_create_sync(db, category_data))

    async def find_or_create_with_parent(
        self,
        category_name: str,
        subcategory_name: Optional[str] = None,
    ) -> FindOrCreateResult:
        return await run_db(
            lambda db: self.find_or_create_with_parent_sync(db, category_name, subcategory_name)
        )

    async def find_or_create_category(
        self,
        category_name: str,
        subcategory_name: Optional[str] = None,
    ) -> Category:
        return await run_db(
            lambda db: self.find_or_create_category_sync(db, category_name, subcategory_name)
        )

    async def get_category_tree(self) -> List[CategoryTreeDto]:
        """Get all categories organized in a tree structure."""
        def _get(db: Session) -> List[CategoryTreeDto]:
            result = db.execute(
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

        return await run_db(_get)

    async def get_all_categories(self) -> List[CategoryResponseDto]:
        """Get all categories as a flat list with hierarchy information."""
        def _get(db: Session) -> List[CategoryResponseDto]:
            result = db.execute(
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

        return await run_db(_get)

    async def get_recent_categories(
        self, user_id: int, limit: int = 10
    ) -> Dict[Literal["categories"], Sequence[Category]]:
        """Fetch recent categories used by the user."""
        def _get(db: Session):
            sql = text(GET_RECENT_CATEGORIES)
            result = db.execute(sql, {"user_id": user_id, "limit": limit})

            if result is None:
                return {"categories": []}

            categories = result.scalars().all()
            return {"categories": categories}

        return await run_db(_get)

    async def get_categories_with_usage_count(
        self, user_id: int
    ) -> List[Dict]:
        """Get categories with their usage count for the user."""
        def _get(db: Session) -> List[Dict]:
            sql = text(GET_CATEGORIES_WITH_USAGE_COUNT)
            result = db.execute(sql, {"user_id": user_id})

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

        return await run_db(_get)
