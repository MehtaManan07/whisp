from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict


from app.agents.intent_classifier.agent import IntentClassificationResult
from app.core.db.engine import get_db
from app.modules.expenses.service import ExpensesService, ExpenseNotFoundError
from app.modules.expenses.dto import CreateExpenseModel
from app.modules.expenses.models import Expense
from app.modules.expenses.schema import ExpenseSchema

router = APIRouter(prefix="/expenses", tags=["expenses"])
expenses_service = ExpensesService()


@router.post("/")
async def create_expense(
    expense_data: CreateExpenseModel, db: AsyncSession = Depends(get_db)
) -> None:
    """API endpoint to create a new expense"""
    try:
        return await expenses_service.create_expense(db, expense_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{expense_id}")
async def delete_expense(expense_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """API endpoint to delete an expense"""
    try:
        await expenses_service.delete_expense(db, expense_id)
    except ExpenseNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{expense_id}")
async def update_expense(
    expense_id: int, update_data: dict, db: AsyncSession = Depends(get_db)
) -> None:
    """API endpoint to update an expense"""
    try:
        return await expenses_service.update_expense(db, expense_id, update_data)
    except ExpenseNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/", response_model=dict[str, List[ExpenseSchema]])
async def get_all_expenses_for_user(
    user_id: int, db: AsyncSession = Depends(get_db)
) -> Dict[str, List[Expense]]:
    """API endpoint to fetch all expenses for a user"""
    return await expenses_service.get_all_expenses_for_user(db, user_id)


@router.get("/category/{category_id}", response_model=dict[str, List[ExpenseSchema]])
async def get_expenses_by_category(
    user_id: int, category_id: int, db: AsyncSession = Depends(get_db)
) -> Dict[str, List[Expense]]:
    """API endpoint to fetch expenses by category for a user"""
    return await expenses_service.get_expenses_by_category(db, user_id, category_id)


@router.post("/demoo")
async def demo_intent(text: str) -> IntentClassificationResult:
    """API endpoint to demo intent classification"""
    return await expenses_service.demo_intent(text)
