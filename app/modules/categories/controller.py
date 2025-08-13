from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Optional

from app.core.db.engine import get_db
from app.modules.categories.service import CategoriesService
from app.modules.categories.dto import (
    CreateCategoryDto,
    CategoryResponseDto,
    CategoryTreeDto,
)

router = APIRouter(prefix="/categories", tags=["categories"])
categories_service = CategoriesService()


@router.post("/", response_model=dict)
async def create_category(
    category_data: CreateCategoryDto, db: AsyncSession = Depends(get_db)
):
    """API endpoint to create a new category or find existing one"""
    try:
        return await categories_service.find_or_create(db, category_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/with-parent", response_model=dict)
async def create_category_with_parent(
    category_name: str,
    subcategory_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """API endpoint to create category and subcategory"""
    try:
        return await categories_service.find_or_create_with_parent(
            db, category_name, subcategory_name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tree", response_model=List[CategoryTreeDto])
async def get_category_tree(
    db: AsyncSession = Depends(get_db),
) -> List[CategoryTreeDto]:
    """API endpoint to get all categories organized in tree structure"""
    try:
        return await categories_service.get_category_tree(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[CategoryResponseDto])
async def get_all_categories(
    db: AsyncSession = Depends(get_db),
) -> List[CategoryResponseDto]:
    """API endpoint to get all categories as flat list"""
    try:
        return await categories_service.get_all_categories(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent")
async def get_recent_categories(
    user_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """API endpoint to get recent categories used by user"""
    try:
        return await categories_service.get_recent_categories(db, user_id, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage")
async def get_categories_with_usage_count(
    user_id: int, db: AsyncSession = Depends(get_db)
) -> List[Dict]:
    """API endpoint to get categories with usage count for user"""
    try:
        return await categories_service.get_categories_with_usage_count(db, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
