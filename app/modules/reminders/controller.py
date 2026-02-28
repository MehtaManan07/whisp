from fastapi import APIRouter, Path, Query, Body, Header, HTTPException, Depends
from typing import List, Optional, Dict, Any
from datetime import timedelta
import logging

from app.core.dependencies import (
    ReminderServiceDep,
    UserServiceDep,
    WhatsAppServiceDep,
)
from app.core.exceptions import ValidationError
from app.core.config import config
from app.modules.reminders.dto import (
    CreateReminderDTO,
    UpdateReminderDTO,
    ListRemindersDTO,
    ReminderResponseDTO,
    ReminderListResponseDTO,
    SnoozeReminderDTO,
)
from app.modules.reminders.types import ReminderType

router = APIRouter(prefix="/reminders", tags=["reminders"])
logger = logging.getLogger(__name__)


def verify_process_token(x_process_token: str = Header(alias="x-process-token")):
    if not config.reminders_process_token:
        logger.error("REMINDERS_PROCESS_TOKEN not configured in environment")
        raise HTTPException(status_code=500, detail="Process token not configured")

    if not x_process_token:
        logger.warning("Process endpoint called without token")
        raise HTTPException(status_code=401, detail="Missing authentication token")

    if x_process_token != config.reminders_process_token:
        logger.warning(f"Process endpoint called with invalid token")
        raise HTTPException(status_code=403, detail="Invalid authentication token")

    return True


@router.post("/", response_model=ReminderResponseDTO, status_code=201)
async def create_reminder(
    data: CreateReminderDTO,
    reminder_service: ReminderServiceDep,
    user_service: UserServiceDep,
    user_id: int = Query(..., description="User ID"),
):
    """Create a new reminder"""
    if user_id <= 0:
        raise ValidationError("User ID must be a positive integer")

    user = await user_service.get_user_by_id(user_id)
    user_timezone = user.timezone if user else "UTC"

    reminder = await reminder_service.create_reminder(
        user_id, data, user_timezone=user_timezone or "UTC"
    )
    return ReminderResponseDTO.model_validate(reminder)


@router.get("/{reminder_id}", response_model=ReminderResponseDTO)
async def get_reminder(
    reminder_id: int,
    reminder_service: ReminderServiceDep,
    user_id: int = Query(..., description="User ID"),
):
    """Get a specific reminder by ID"""
    if user_id <= 0:
        raise ValidationError("User ID must be a positive integer")

    reminder = await reminder_service.get_reminder(reminder_id, user_id)
    return ReminderResponseDTO.model_validate(reminder)


@router.get("/", response_model=ReminderListResponseDTO)
async def list_reminders(
    reminder_service: ReminderServiceDep,
    user_id: int = Query(..., description="User ID"),
    reminder_type: Optional[ReminderType] = Query(None, description="Filter by reminder type"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
):
    """List all reminders for a user with optional filters"""
    if user_id <= 0:
        raise ValidationError("User ID must be a positive integer")

    list_dto = ListRemindersDTO(
        user_id=user_id, reminder_type=reminder_type, is_active=is_active
    )
    reminders = await reminder_service.list_reminders(list_dto)
    reminder_dtos = [ReminderResponseDTO.model_validate(r) for r in reminders]
    active_count = sum(1 for r in reminders if r.is_active)

    return ReminderListResponseDTO(
        reminders=reminder_dtos, total=len(reminders), active_count=active_count
    )


@router.put("/{reminder_id}", response_model=ReminderResponseDTO)
async def update_reminder(
    data: UpdateReminderDTO,
    reminder_id: int,
    reminder_service: ReminderServiceDep,
    user_service: UserServiceDep,
    user_id: int = Query(..., description="User ID"),
):
    """Update an existing reminder"""
    if user_id <= 0:
        raise ValidationError("User ID must be a positive integer")

    user = await user_service.get_user_by_id(user_id)
    user_timezone = user.timezone if user else "UTC"

    reminder = await reminder_service.update_reminder(
        reminder_id, user_id, data, user_timezone=user_timezone or "UTC"
    )
    return ReminderResponseDTO.model_validate(reminder)


@router.delete("/{reminder_id}", status_code=204)
async def delete_reminder(
    reminder_id: int,
    reminder_service: ReminderServiceDep,
    user_id: int = Query(..., description="User ID"),
):
    """Soft delete a reminder"""
    if user_id <= 0:
        raise ValidationError("User ID must be a positive integer")

    await reminder_service.delete_reminder(reminder_id, user_id)
    return None


@router.post("/{reminder_id}/snooze", response_model=ReminderResponseDTO)
async def snooze_reminder(
    data: SnoozeReminderDTO,
    reminder_id: int,
    reminder_service: ReminderServiceDep,
    user_id: int = Query(..., description="User ID"),
):
    """Snooze a reminder by postponing its next trigger time"""
    if user_id <= 0:
        raise ValidationError("User ID must be a positive integer")

    duration = timedelta(minutes=data.duration_minutes)
    reminder = await reminder_service.snooze_reminder(reminder_id, user_id, duration)
    return ReminderResponseDTO.model_validate(reminder)


@router.post("/{reminder_id}/complete", response_model=ReminderResponseDTO)
async def complete_reminder(
    reminder_id: int,
    reminder_service: ReminderServiceDep,
    user_service: UserServiceDep,
    user_id: int = Query(..., description="User ID"),
):
    """Mark a reminder as completed"""
    if user_id <= 0:
        raise ValidationError("User ID must be a positive integer")

    user = await user_service.get_user_by_id(user_id)
    user_timezone = user.timezone if user else "UTC"

    reminder = await reminder_service.complete_reminder(
        reminder_id, user_id, user_timezone=user_timezone or "UTC"
    )
    return ReminderResponseDTO.model_validate(reminder)


@router.get("/due/list", response_model=List[ReminderResponseDTO])
async def get_due_reminders(
    reminder_service: ReminderServiceDep,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of due reminders to fetch"),
):
    """Get all reminders that are due for triggering (internal use)"""
    reminders = await reminder_service.get_due_reminders(limit)
    return [ReminderResponseDTO.model_validate(r) for r in reminders]


@router.post("/fix-overdue", status_code=200)
async def fix_overdue_reminders(
    reminder_service: ReminderServiceDep,
    user_service: UserServiceDep,
    user_id: Optional[int] = Query(None, description="User ID to fix reminders for"),
):
    """Fix overdue recurring reminders by recalculating their next trigger times."""
    user = await user_service.get_user_by_id(user_id) if user_id else None
    user_timezone = user.timezone if user else "UTC"
    fixed_count = await reminder_service.fix_overdue_reminders(
        user_id, user_timezone=user_timezone or "UTC"
    )
    return {
        "message": f"Fixed {fixed_count} overdue reminder(s)",
        "fixed_count": fixed_count,
        "user_id": user_id,
    }


@router.post(
    "/{reminder_id}/process",
    status_code=200,
    dependencies=[Depends(verify_process_token)],
)
async def process_triggered_reminder(
    reminder_id: int,
    reminder_service: ReminderServiceDep,
    user_service: UserServiceDep,
    whatsapp_service: WhatsAppServiceDep,
):
    """Process a specific reminder by ID (called by cron jobs)."""
    return await reminder_service.process_single_reminder(
        reminder_id=reminder_id,
        user_service=user_service,
        whatsapp_service=whatsapp_service,
    )
