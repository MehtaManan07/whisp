from fastapi import APIRouter, Depends
from typing import List, Dict, Literal

from app.intelligence.intent.types import CLASSIFIED_RESULT
from app.core.dependencies import (
    DatabaseDep,
    ExpenseServiceDep,
    ExtractorDep,
    IntentClassifierDep,
)
from app.core.exceptions import ExpenseNotFoundError, ValidationError, DatabaseError
from app.modules.expenses.dto import (
    CreateExpenseModel,
    DeleteExpenseModel,
    GetAllExpensesModel,
)
from app.modules.expenses.models import Expense

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.post("/")
async def create_expense(
    expense_data: CreateExpenseModel,
    db: DatabaseDep,
    expenses_service: ExpenseServiceDep,
) -> None:
    """API endpoint to create a new expense"""
    if not expense_data.amount or expense_data.amount <= 0:
        raise ValidationError("Amount must be greater than 0")
    
    if not expense_data.user_id:
        raise ValidationError("User ID is required")
    
    await expenses_service.create_expense(db, expense_data)


@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: int,
    db: DatabaseDep,
    expenses_service: ExpenseServiceDep,
) -> None:
    """API endpoint to delete an expense"""
    if expense_id <= 0:
        raise ValidationError("Expense ID must be a positive integer")
    
    await expenses_service.delete_expense(db, DeleteExpenseModel(id=expense_id))


@router.put("/{expense_id}")
async def update_expense(
    expense_id: int,
    update_data: dict,
    db: DatabaseDep,
    expenses_service: ExpenseServiceDep,
) -> None:
    """API endpoint to update an expense"""
    if expense_id <= 0:
        raise ValidationError("Expense ID must be a positive integer")
    
    if not update_data:
        raise ValidationError("Update data cannot be empty")
    
    await expenses_service.update_expense(db, expense_id, update_data)


@router.get("/")
async def get_all_expenses(
    db: DatabaseDep,
    expenses_service: ExpenseServiceDep,
    data: GetAllExpensesModel = Depends(GetAllExpensesModel),
):
    """API endpoint to fetch all expenses for a user"""
    if not data.user_id:
        raise ValidationError("User ID is required")
    
    return await expenses_service.get_expenses(db=db, data=data)


@router.post("/demo")
async def demo_intent(
    text: str,
    db: DatabaseDep,
    expenses_service: ExpenseServiceDep,
    intent_classifier: IntentClassifierDep,
    extractor: ExtractorDep,
) -> CLASSIFIED_RESULT:
    """API endpoint to demo intent classification"""
    if not text or not text.strip():
        raise ValidationError("Text input is required")
    
    return await expenses_service.demo_intent(
        db=db,
        text=text,
        intent_classifier=intent_classifier,
        extractor=extractor,
    )
