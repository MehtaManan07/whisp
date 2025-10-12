from fastapi import APIRouter, Path, Query
from typing import List, Optional
from datetime import timedelta

from app.core.dependencies import DatabaseDep, ReminderServiceDep
from app.core.exceptions import ValidationError
from app.modules.reminders.dto import (
    CreateReminderDTO,
    UpdateReminderDTO,
    ReminderResponseDTO,
    ReminderListResponseDTO,
    SnoozeReminderDTO,
)
from app.modules.reminders.types import ReminderType

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.post("/", response_model=ReminderResponseDTO, status_code=201)
async def create_reminder(
    data: CreateReminderDTO,
    db: DatabaseDep,
    reminder_service: ReminderServiceDep,
    user_id: int = Query(..., description="User ID"),
):
    """Create a new reminder"""
    if user_id <= 0:
        raise ValidationError("User ID must be a positive integer")
    
    reminder = await reminder_service.create_reminder(db, user_id, data)
    return ReminderResponseDTO.model_validate(reminder)


@router.get("/{reminder_id}", response_model=ReminderResponseDTO)
async def get_reminder(
    reminder_id: int,
    db: DatabaseDep,
    reminder_service: ReminderServiceDep,
    user_id: int = Query(..., description="User ID"),
):
    """Get a specific reminder by ID"""
    if user_id <= 0:
        raise ValidationError("User ID must be a positive integer")
    
    reminder = await reminder_service.get_reminder(db, reminder_id, user_id)
    return ReminderResponseDTO.model_validate(reminder)


@router.get("/", response_model=ReminderListResponseDTO)
async def list_reminders(
    db: DatabaseDep,
    reminder_service: ReminderServiceDep,
    user_id: int = Query(..., description="User ID"),
    reminder_type: Optional[ReminderType] = Query(None, description="Filter by reminder type"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
):
    """List all reminders for a user with optional filters"""
    if user_id <= 0:
        raise ValidationError("User ID must be a positive integer")
    
    reminders = await reminder_service.list_reminders(db, user_id, reminder_type, is_active)
    reminder_dtos = [ReminderResponseDTO.model_validate(r) for r in reminders]
    active_count = sum(1 for r in reminders if r.is_active)
    
    return ReminderListResponseDTO(
        reminders=reminder_dtos,
        total=len(reminders),
        active_count=active_count
    )


@router.put("/{reminder_id}", response_model=ReminderResponseDTO)
async def update_reminder(
    data: UpdateReminderDTO,
    reminder_id: int,
    db: DatabaseDep,
    reminder_service: ReminderServiceDep,
    user_id: int = Query(..., description="User ID"),
):
    """Update an existing reminder"""
    if user_id <= 0:
        raise ValidationError("User ID must be a positive integer")
    
    reminder = await reminder_service.update_reminder(db, reminder_id, user_id, data)
    return ReminderResponseDTO.model_validate(reminder)


@router.delete("/{reminder_id}", status_code=204)
async def delete_reminder(
    reminder_id: int,
    db: DatabaseDep,
    reminder_service: ReminderServiceDep,
    user_id: int = Query(..., description="User ID"),
):
    """Soft delete a reminder"""
    if user_id <= 0:
        raise ValidationError("User ID must be a positive integer")
    
    await reminder_service.delete_reminder(db, reminder_id, user_id)
    return None


@router.post("/{reminder_id}/snooze", response_model=ReminderResponseDTO)
async def snooze_reminder(
    data: SnoozeReminderDTO,
    reminder_id: int,
    db: DatabaseDep,
    reminder_service: ReminderServiceDep,
    user_id: int = Query(..., description="User ID"),
):
    """Snooze a reminder by postponing its next trigger time"""
    if user_id <= 0:
        raise ValidationError("User ID must be a positive integer")
    
    duration = timedelta(minutes=data.duration_minutes)
    reminder = await reminder_service.snooze_reminder(db, reminder_id, user_id, duration)
    return ReminderResponseDTO.model_validate(reminder)


@router.post("/{reminder_id}/complete", response_model=ReminderResponseDTO)
async def complete_reminder(
    reminder_id: int,
    db: DatabaseDep,
    reminder_service: ReminderServiceDep,
    user_id: int = Query(..., description="User ID"),
):
    """Mark a reminder as completed (one-time) or schedule next occurrence (recurring)"""
    if user_id <= 0:
        raise ValidationError("User ID must be a positive integer")
    
    reminder = await reminder_service.complete_reminder(db, reminder_id, user_id)
    return ReminderResponseDTO.model_validate(reminder)


@router.get("/due/list", response_model=List[ReminderResponseDTO])
async def get_due_reminders(
    db: DatabaseDep,
    reminder_service: ReminderServiceDep,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of due reminders to fetch"),
):
    """Get all reminders that are due for triggering (internal use)"""
    reminders = await reminder_service.get_due_reminders(db, limit)
    return [ReminderResponseDTO.model_validate(r) for r in reminders]
