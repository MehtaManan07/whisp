from fastapi import APIRouter, Depends, Query
from typing import List, Dict, Optional

from app.core.dependencies import CategoryServiceDep
from app.core.exceptions import ValidationError
from app.modules.categories.dto import (
    CreateCategoryDto,
    CategoryResponseDto,
    CategoryTreeDto,
)

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("/", response_model=dict)
async def create_category(
    category_data: CreateCategoryDto,
    categories_service: CategoryServiceDep,
):
    """API endpoint to create a new category or find existing one"""
    if not category_data.name or not category_data.name.strip():
        raise ValidationError("Category name is required")

    return await categories_service.find_or_create(category_data)


@router.post("/with-parent", response_model=dict)
async def create_category_with_parent(
    category_name: str,
    categories_service: CategoryServiceDep,
    subcategory_name: Optional[str] = None,
):
    """API endpoint to create category and subcategory"""
    if not category_name or not category_name.strip():
        raise ValidationError("Category name is required")

    return await categories_service.find_or_create_with_parent(
        category_name, subcategory_name
    )


@router.get("/tree", response_model=List[CategoryTreeDto])
async def get_category_tree(
    categories_service: CategoryServiceDep,
) -> List[CategoryTreeDto]:
    """API endpoint to get all categories organized in tree structure"""
    return await categories_service.get_category_tree()


@router.get("/", response_model=List[CategoryResponseDto])
async def get_all_categories(
    categories_service: CategoryServiceDep,
) -> List[CategoryResponseDto]:
    """API endpoint to get all categories as flat list"""
    return await categories_service.get_all_categories()


@router.get("/recent")
async def get_recent_categories(
    user_id: int,
    categories_service: CategoryServiceDep,
    limit: int = Query(default=10, ge=1, le=50),
) -> dict:
    """API endpoint to get recent categories used by user"""
    if user_id <= 0:
        raise ValidationError("User ID must be a positive integer")

    if limit <= 0 or limit > 50:
        raise ValidationError("Limit must be between 1 and 50")

    return await categories_service.get_recent_categories(user_id, limit)


@router.get("/usage")
async def get_categories_with_usage_count(
    user_id: int,
    categories_service: CategoryServiceDep,
) -> List[Dict]:
    """API endpoint to get categories with usage count for user"""
    if user_id <= 0:
        raise ValidationError("User ID must be a positive integer")

    return await categories_service.get_categories_with_usage_count(user_id)
