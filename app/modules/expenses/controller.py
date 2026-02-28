from fastapi import APIRouter, Depends
from typing import List, Dict, Literal

from app.intelligence.intent.types import CLASSIFIED_RESULT
from app.core.dependencies import (
    ExpenseServiceDep,
    IntentClassifierDep,
    LLMServiceDep,
    CategoryClassifierDep,
)
from app.core.exceptions import ValidationError
from app.modules.expenses.dto import (
    CreateExpenseModel,
    DeleteExpenseModel,
    GetAllExpensesModel,
)

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.post("/")
async def create_expense(
    expense_data: CreateExpenseModel,
    expenses_service: ExpenseServiceDep,
) -> None:
    """API endpoint to create a new expense"""
    if not expense_data.amount or expense_data.amount <= 0:
        raise ValidationError("Amount must be greater than 0")

    if not expense_data.user_id:
        raise ValidationError("User ID is required")

    await expenses_service.create_expense(expense_data)


@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: int,
    expenses_service: ExpenseServiceDep,
) -> None:
    """API endpoint to delete an expense"""
    if expense_id <= 0:
        raise ValidationError("Expense ID must be a positive integer")

    await expenses_service.delete_expense(DeleteExpenseModel(id=expense_id))


@router.put("/{expense_id}")
async def update_expense(
    expense_id: int,
    update_data: dict,
    expenses_service: ExpenseServiceDep,
) -> None:
    """API endpoint to update an expense"""
    if expense_id <= 0:
        raise ValidationError("Expense ID must be a positive integer")

    if not update_data:
        raise ValidationError("Update data cannot be empty")

    await expenses_service.update_expense(expense_id, update_data)


@router.get("/")
async def get_all_expenses(
    expenses_service: ExpenseServiceDep,
    data: GetAllExpensesModel = Depends(GetAllExpensesModel),
):
    """API endpoint to fetch all expenses for a user"""
    if not data.user_id:
        raise ValidationError("User ID is required")

    return await expenses_service.get_expenses(data=data)


@router.post("/demo")
async def demo_intent(
    text: str,
    intent_classifier: IntentClassifierDep,
    llm_service: LLMServiceDep,
    category_classifier: CategoryClassifierDep,
) -> CLASSIFIED_RESULT:
    """API endpoint to demo intent classification"""
    if not text or not text.strip():
        raise ValidationError("Text input is required")

    from app.intelligence.extraction.extractor import extract_dto

    user_id = 2  # Demo user
    intent = await intent_classifier.classify(text)
    dto = await extract_dto(
        message=text,
        intent=intent,
        user_id=user_id,
        llm_service=llm_service,
        category_classifier=category_classifier,
    )

    return (dto, intent)
