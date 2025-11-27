import logging
from typing import List
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import DatabaseDep
from app.core.exceptions import ValidationError
from app.modules.budgets.dto import (
    CreateBudgetDTO,
    UpdateBudgetDTO,
    GetBudgetDTO,
    ViewBudgetProgressDTO,
    DeleteBudgetDTO,
    BudgetResponseDTO,
    BudgetProgressResponseDTO,
    BudgetListResponseDTO,
)
from app.modules.budgets.service import BudgetService
from app.modules.budgets.types import BudgetPeriod

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/budgets", tags=["budgets"])


def get_budget_service() -> BudgetService:
    """Dependency to get BudgetService instance."""
    return BudgetService()


@router.post("", response_model=BudgetResponseDTO)
async def create_budget(
    data: CreateBudgetDTO,
    db: DatabaseDep,
    service: BudgetService = Depends(get_budget_service),
) -> BudgetResponseDTO:
    """Create a new budget."""
    return await service.create_budget(db=db, data=data)


@router.get("", response_model=BudgetListResponseDTO)
async def list_budgets(
    db: DatabaseDep,
    user_id: int = Query(..., description="User ID"),
    category_name: str = Query(None, description="Filter by category name"),
    period: BudgetPeriod = Query(None, description="Filter by period"),
    is_active: bool = Query(True, description="Filter by active status"),
    service: BudgetService = Depends(get_budget_service),
) -> BudgetListResponseDTO:
    """List budgets with optional filters."""
    get_dto = GetBudgetDTO(
        user_id=user_id,
        category_name=category_name,
        period=period,
        is_active=is_active,
    )
    budgets = await service.get_budgets(db=db, data=get_dto)
    
    total = len(budgets)
    active_count = sum(1 for b in budgets if b.is_active)
    
    return BudgetListResponseDTO(
        budgets=budgets,
        total=total,
        active_count=active_count,
    )


@router.get("/{budget_id}", response_model=BudgetResponseDTO)
async def get_budget(
    db: DatabaseDep,
    budget_id: int = Path(..., description="Budget ID"),
    service: BudgetService = Depends(get_budget_service),
) -> BudgetResponseDTO:
    """Get a single budget by ID."""
    budget = await service.get_budget_by_id(db=db, budget_id=budget_id)
    if not budget:
        raise ValidationError(f"Budget with ID {budget_id} not found")
    return budget


@router.get("/{budget_id}/progress", response_model=BudgetProgressResponseDTO)
async def get_budget_progress_by_id(
    db: DatabaseDep,
    budget_id: int = Path(..., description="Budget ID"),
    service: BudgetService = Depends(get_budget_service),
) -> BudgetProgressResponseDTO:
    """Get budget progress for a specific budget."""
    # First get the budget
    budget = await service.get_budget_by_id(db=db, budget_id=budget_id)
    if not budget:
        raise ValidationError(f"Budget with ID {budget_id} not found")
    
    # Create DTO for progress calculation
    progress_dto = ViewBudgetProgressDTO(
        user_id=budget.user_id,
        category_name=budget.category_name,
        period=budget.period,
    )
    
    progress_list = await service.get_budget_progress(db=db, data=progress_dto)
    
    # Find the matching budget in the progress list
    for progress in progress_list:
        if progress.budget.id == budget_id:
            return progress
    
    raise ValidationError(f"Could not calculate progress for budget {budget_id}")


@router.get("/progress/all", response_model=List[BudgetProgressResponseDTO])
async def get_all_budget_progress(
    db: DatabaseDep,
    user_id: int = Query(..., description="User ID"),
    category_name: str = Query(None, description="Filter by category name"),
    period: BudgetPeriod = Query(None, description="Filter by period"),
    service: BudgetService = Depends(get_budget_service),
) -> List[BudgetProgressResponseDTO]:
    """Get budget progress for all matching budgets."""
    progress_dto = ViewBudgetProgressDTO(
        user_id=user_id,
        category_name=category_name,
        period=period,
    )
    return await service.get_budget_progress(db=db, data=progress_dto)


@router.put("/{budget_id}", response_model=BudgetResponseDTO)
async def update_budget(
    data: UpdateBudgetDTO,
    db: DatabaseDep,
    budget_id: int = Path(..., description="Budget ID"),
    user_id: int = Query(..., description="User ID for verification"),
    service: BudgetService = Depends(get_budget_service),
) -> BudgetResponseDTO:
    """Update an existing budget."""
    # Set the budget_id from path parameter
    data.budget_id = budget_id
    
    return await service.update_budget(db=db, data=data, user_id=user_id)


@router.delete("/{budget_id}")
async def delete_budget(
    db: DatabaseDep,
    budget_id: int = Path(..., description="Budget ID"),
    user_id: int = Query(..., description="User ID for verification"),
    service: BudgetService = Depends(get_budget_service),
) -> dict:
    """Delete a budget (soft delete)."""
    delete_dto = DeleteBudgetDTO(budget_id=budget_id, user_id=user_id)
    success = await service.delete_budget(db=db, data=delete_dto)
    
    return {"success": success, "message": "Budget deleted successfully"}

