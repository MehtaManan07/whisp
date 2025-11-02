# app/modules/reminders/service.py

from datetime import datetime, timedelta
from typing import Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select
import logging

from app.modules.reminders.models import Reminder
from app.modules.reminders.types import RecurrenceType, RecurrenceConfig
from app.modules.reminders.dto import (
    CreateReminderDTO,
    UpdateReminderDTO,
    ListRemindersDTO,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.modules.reminders.utils import RemindersUtils
from app.utils.datetime import utc_now, parse_time_in_user_tz, to_user_timezone, to_utc
from app.core.scheduler import Scheduler
from app.core.config import config

logger = logging.getLogger(__name__)


class ReminderService:
    """Service for managing reminders."""

    def __init__(self):
        self.scheduler = Scheduler()
        self.logger = logger

    async def create_reminder(
        self,
        db: AsyncSession,
        user_id: int,
        data: CreateReminderDTO,
        user_timezone: str = "UTC",
    ) -> Reminder:
        """Create a new reminder with timezone-aware scheduling.

        Args:
            db: Database session
            user_id: User ID
            data: Reminder creation data
            user_timezone: User's IANA timezone (e.g., 'Asia/Kolkata')
        """
        # Validate recurrence config
        if data.recurrence_type != RecurrenceType.ONCE and not data.recurrence_config:
            raise ValidationError("Recurrence config required for recurring reminders")

        try:
            # Calculate initial trigger time (in user's timezone, converted to UTC for storage)
            next_trigger = self._calculate_next_trigger(
                base_time=data.next_trigger_at or utc_now(),
                recurrence_type=data.recurrence_type,
                recurrence_config=data.recurrence_config,
                user_timezone=user_timezone,
            )

            reminder = Reminder(
                user_id=user_id,
                reminder_type=data.reminder_type,
                title=data.title,
                description=data.description,
                amount=data.amount,
                category_id=data.category_id,
                recurrence_type=data.recurrence_type,
                recurrence_config=(
                    data.recurrence_config.dict() if data.recurrence_config else None
                ),
                next_trigger_at=next_trigger,
                is_active=True,
            )

            db.add(reminder)
            await db.commit()
            await db.refresh(reminder)

            # Schedule the reminder with QStash if scheduler is provided
            try:
                schedule_id = await self._schedule_reminder(
                    reminder=reminder,
                    user_timezone=user_timezone,
                )
                reminder.schedule_id = schedule_id
                await db.commit()
                await db.refresh(reminder)
                logger.info(
                    f"Scheduled reminder {reminder.id} with QStash (schedule_id={schedule_id})"
                )
            except Exception as e:
                logger.error(
                    f"Failed to schedule reminder {reminder.id} with QStash: {e}"
                )
                # Don't fail the entire operation if scheduling fails
                # The reminder is still created in the database

            return reminder

        except Exception as e:
            await db.rollback()
            raise

    async def get_reminder(
        self, db: AsyncSession, reminder_id: int, user_id: int
    ) -> Reminder:
        """Get a specific reminder."""
        result = await db.execute(
            select(Reminder).where(
                and_(
                    Reminder.id == reminder_id,
                    Reminder.user_id == user_id,
                    Reminder.deleted_at.is_(None),
                )
            )
        )
        reminder = result.scalar_one_or_none()

        if not reminder:
            raise NotFoundError(
                f"Reminder {reminder_id} not found", resource_id=str(reminder_id)
            )

        return reminder

    async def list_reminders(
        self,
        db: AsyncSession,
        data: ListRemindersDTO,
    ) -> List[Reminder]:
        """List user's reminders with optional filters."""
        conditions = [Reminder.user_id == data.user_id, Reminder.deleted_at.is_(None)]

        if data.reminder_type:
            conditions.append(Reminder.reminder_type == data.reminder_type)

        if data.is_active is not None:
            conditions.append(Reminder.is_active == data.is_active)

        result = await db.execute(
            select(Reminder).where(and_(*conditions)).order_by(Reminder.next_trigger_at)
        )
        return list(result.scalars().all())

    async def update_reminder(
        self,
        db: AsyncSession,
        reminder_id: int,
        user_id: int,
        data: UpdateReminderDTO,
        user_timezone: str = "UTC",
    ) -> Reminder:
        """Update an existing reminder with timezone awareness.

        Args:
            db: Database session
            reminder_id: Reminder ID
            user_id: User ID
            data: Update data
            user_timezone: User's IANA timezone (e.g., 'Asia/Kolkata')
        """
        reminder = await self.get_reminder(db, reminder_id, user_id)
        old_schedule_id = reminder.schedule_id

        try:
            # Update simple fields efficiently using model_dump
            update_data = data.model_dump(
                exclude_unset=True, exclude={"recurrence_type", "recurrence_config"}
            )
            for field, value in update_data.items():
                setattr(reminder, field, value)

            # Update recurrence if changed
            recurrence_changed = False
            if data.recurrence_type is not None or data.recurrence_config is not None:
                recurrence_type = data.recurrence_type or RecurrenceType(
                    reminder.recurrence_type
                )
                recurrence_config = data.recurrence_config or reminder.recurrence_config

                reminder.recurrence_type = recurrence_type
                reminder.recurrence_config = (
                    recurrence_config.model_dump()
                    if isinstance(recurrence_config, RecurrenceConfig)
                    else recurrence_config
                )

                # Recalculate next trigger
                reminder.next_trigger_at = self._calculate_next_trigger(
                    base_time=utc_now(),
                    recurrence_type=recurrence_type,
                    recurrence_config=(
                        RecurrenceConfig.model_validate(reminder.recurrence_config)
                        if reminder.recurrence_config
                        else None
                    ),
                    user_timezone=user_timezone,
                )
                recurrence_changed = True

            await db.commit()
            await db.refresh(reminder)

            # Reschedule if scheduler provided and recurrence changed or is_active changed
            if recurrence_changed or data.is_active is not None:
                try:
                    # Cancel old schedule if exists
                    if old_schedule_id:
                        await self._cancel_schedule(old_schedule_id)

                    # Schedule new reminder if active
                    if reminder.is_active:
                        schedule_id = await self._schedule_reminder(
                            reminder=reminder,
                            user_timezone=user_timezone,
                        )
                        reminder.schedule_id = schedule_id
                        await db.commit()
                        await db.refresh(reminder)
                        logger.info(
                            f"Rescheduled reminder {reminder.id} (schedule_id={schedule_id})"
                        )
                    else:
                        reminder.schedule_id = None
                        await db.commit()
                        await db.refresh(reminder)
                except Exception as e:
                    logger.error(f"Failed to reschedule reminder {reminder.id}: {e}")

            return reminder

        except Exception as e:
            await db.rollback()
            raise

    async def delete_reminder(
        self,
        db: AsyncSession,
        reminder_id: int,
        user_id: int,
    ) -> None:
        """Soft delete a reminder by marking deleted_at and canceling schedule.

        Args:
            db: Database session
            reminder_id: Reminder ID
            user_id: User ID
        """
        reminder = await self.get_reminder(db, reminder_id, user_id)
        schedule_id = reminder.schedule_id

        try:
            reminder.deleted_at = utc_now()
            reminder.is_active = False
            await db.commit()

            # Cancel the schedule if exists
            if schedule_id:
                try:
                    await self._cancel_schedule(schedule_id)
                    logger.info(
                        f"Canceled schedule {schedule_id} for deleted reminder {reminder_id}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to cancel schedule for reminder {reminder_id}: {e}"
                    )

        except Exception as e:
            await db.rollback()
            raise

    async def snooze_reminder(
        self, db: AsyncSession, reminder_id: int, user_id: int, duration: timedelta
    ) -> Reminder:
        """Snooze a reminder by postponing its next trigger time."""
        reminder = await self.get_reminder(db, reminder_id, user_id)
        reminder.next_trigger_at = utc_now() + duration

        try:
            await db.commit()
            await db.refresh(reminder)
            return reminder
        except Exception as e:
            await db.rollback()
            raise

    async def complete_reminder(
        self,
        db: AsyncSession,
        reminder_id: int,
        user_id: int,
        user_timezone: str = "UTC",
    ) -> Reminder:
        """Mark a reminder as completed with timezone awareness.

        Args:
            db: Database session
            reminder_id: Reminder ID
            user_id: User ID
            user_timezone: User's IANA timezone (e.g., 'Asia/Kolkata')
        """
        reminder = await self.get_reminder(db, reminder_id, user_id)

        try:
            if reminder.is_recurring:
                # Calculate next occurrence
                reminder.last_triggered_at = utc_now()
                reminder.next_trigger_at = self._calculate_next_trigger(
                    base_time=utc_now(),
                    recurrence_type=RecurrenceType(reminder.recurrence_type),
                    recurrence_config=(
                        RecurrenceConfig.model_validate(reminder.recurrence_config)
                        if reminder.recurrence_config
                        else None
                    ),
                    user_timezone=user_timezone,
                )
            else:
                # One-time reminder - deactivate
                reminder.is_active = False
                reminder.last_triggered_at = utc_now()

            await db.commit()
            await db.refresh(reminder)

            return reminder

        except Exception as e:
            await db.rollback()
            raise

    async def get_due_reminders(
        self, db: AsyncSession, limit: int = 100
    ) -> List[Reminder]:
        """Get reminders that are due for triggering."""
        result = await db.execute(
            select(Reminder)
            .where(
                and_(
                    Reminder.is_active == True,
                    Reminder.next_trigger_at <= utc_now(),
                    Reminder.deleted_at.is_(None),
                )
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def fix_overdue_reminders(
        self,
        db: AsyncSession,
        user_id: Optional[int] = None,
        user_timezone: str = "UTC",
    ) -> int:
        """
        Fix overdue recurring reminders by recalculating their next trigger times.

        This method is useful after fixing bugs in the trigger calculation logic
        to update existing reminders that are stuck in an overdue state.

        Args:
            db: Database session
            user_id: Optional user ID to limit fix to specific user, None for all users
            user_timezone: User's IANA timezone (e.g., 'Asia/Kolkata')

        Returns:
            Number of reminders fixed
        """
        try:
            # Build query conditions
            conditions = [
                Reminder.is_active == True,
                Reminder.next_trigger_at <= utc_now(),
                Reminder.deleted_at.is_(None),
                Reminder.recurrence_type != "once",  # Only fix recurring reminders
            ]

            if user_id:
                conditions.append(Reminder.user_id == user_id)

            # Get overdue recurring reminders
            result = await db.execute(select(Reminder).where(and_(*conditions)))
            overdue_reminders = list(result.scalars().all())

            fixed_count = 0

            for reminder in overdue_reminders:
                # Recalculate next trigger using current logic
                reminder.next_trigger_at = self._calculate_next_trigger(
                    base_time=utc_now(),
                    recurrence_type=RecurrenceType(reminder.recurrence_type),
                    recurrence_config=(
                        RecurrenceConfig.model_validate(reminder.recurrence_config)
                        if reminder.recurrence_config
                        else None
                    ),
                    user_timezone=user_timezone,
                )
                fixed_count += 1

            await db.commit()
            return fixed_count

        except Exception as e:
            await db.rollback()
            raise
        
    async def trigger_reminder_webhook(
        self,
        db: AsyncSession,
        payload: dict[str, Any],
        user_service,
        whatsapp_service,
    ):
        """
        Webhook endpoint called by QStash when a reminder is due.
        This is an internal endpoint called by the scheduler.
        
        Dependencies are injected to avoid circular imports between
        dependencies.py and service modules.
        
        Args:
            db: Database session
            payload: Webhook payload containing reminder_id and user_id
            user_service: Injected user service instance
            whatsapp_service: Injected WhatsApp service instance
        """
        try:
            reminder_id = payload.get("reminder_id")
            user_id = payload.get("user_id")

            if not reminder_id or not user_id:
                logger.error(f"Webhook called without reminder_id or user_id: {payload}")
                return {"status": "error", "message": "Missing reminder_id or user_id"}

            # Get the reminder using the service method
            reminder = await self.get_reminder(db, reminder_id, user_id)
            if not reminder:
                logger.error(f"Reminder {reminder_id} not found")
                return {"status": "error", "message": "Reminder not found"}

            # Get the user with phone number
            user = await user_service.get_user_by_id(db, user_id)
            if not user or not user.phone_number:
                logger.error(f"User {user_id} not found or has no phone number")
                return {"status": "error", "message": "User not found or no phone number"}

            # Get user timezone
            user_timezone = user_service.get_user_timezone(user) if user else "UTC"

            # Send WhatsApp notification
            try:
                message = f"🔔 Reminder: {reminder.title}"
                if reminder.amount:
                    message += f"\nAmount: ₹{reminder.amount:,.2f}"
                if reminder.description:
                    message += f"\n\n{reminder.description}"

                await whatsapp_service.send_text(user.phone_number, message)
                logger.info(f"Sent reminder {reminder_id} to user {user.phone_number}")
            except Exception as e:
                logger.error(
                    f"Failed to send WhatsApp notification for reminder {reminder_id}: {e}"
                )

            # Process the reminder (mark as triggered, schedule next if recurring)
            await self.process_triggered_reminder(db, reminder, user_timezone)

            return {"status": "success", "reminder_id": reminder_id}

        except Exception as e:
            logger.error(f"Error processing reminder webhook: {e}")
            return {"status": "error", "message": str(e)}


    async def process_triggered_reminder(
        self,
        db: AsyncSession,
        reminder: Reminder,
        user_timezone: str = "UTC",
    ) -> None:
        """Process a reminder after it has been triggered with timezone awareness.

        Args:
            db: Database session
            reminder: Reminder object with user relationship loaded
            user_timezone: User's IANA timezone (e.g., 'Asia/Kolkata')
        """
        try:
            reminder.last_triggered_at = utc_now()

            if reminder.is_recurring:
                # Calculate next trigger time
                reminder.next_trigger_at = self._calculate_next_trigger(
                    base_time=utc_now(),
                    recurrence_type=RecurrenceType(reminder.recurrence_type),
                    recurrence_config=(
                        RecurrenceConfig.model_validate(reminder.recurrence_config)
                        if reminder.recurrence_config
                        else None
                    ),
                    user_timezone=user_timezone,
                )

                # Reschedule for the next occurrence
                try:
                    schedule_id = await self._schedule_reminder(
                        reminder=reminder,
                        user_timezone=user_timezone,
                    )
                    reminder.schedule_id = schedule_id
                    logger.info(
                        f"Rescheduled recurring reminder {reminder.id} (schedule_id={schedule_id})"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to reschedule recurring reminder {reminder.id}: {e}"
                    )
            else:
                # One-time reminder - deactivate
                reminder.is_active = False
                reminder.schedule_id = None

            await db.commit()

        except Exception as e:
            await db.rollback()
            raise

    def _calculate_next_trigger(
        self,
        base_time: datetime,
        recurrence_type: RecurrenceType,
        recurrence_config: Optional[RecurrenceConfig],
        user_timezone: str = "UTC",
    ) -> datetime:
        """Calculate the next trigger time based on recurrence pattern.

        The time calculations happen in the user's timezone, but the result
        is stored in UTC. This ensures reminders trigger at the correct local time.

        Args:
            base_time: Base UTC time to calculate from
            recurrence_type: Type of recurrence
            recurrence_config: Recurrence configuration
            user_timezone: User's IANA timezone (e.g., 'Asia/Kolkata')

        Returns:
            Next trigger time in UTC
        """
        # Parse time from config (this is in user's local timezone)
        target_time = RemindersUtils._parse_target_time(recurrence_config)

        if recurrence_type == RecurrenceType.ONCE:
            return base_time

        # Convert base_time to user's timezone for calculations
        base_time_local = to_user_timezone(base_time, user_timezone)

        if recurrence_type == RecurrenceType.DAILY:
            next_trigger_local = RemindersUtils._calculate_daily_trigger(
                base_time_local, target_time
            )

        elif recurrence_type == RecurrenceType.WEEKLY:
            next_trigger_local = RemindersUtils._calculate_weekly_trigger(
                base_time_local, recurrence_config, target_time
            )

        elif recurrence_type == RecurrenceType.MONTHLY:
            next_trigger_local = RemindersUtils._calculate_monthly_trigger(
                base_time_local, recurrence_config, target_time
            )

        elif recurrence_type == RecurrenceType.YEARLY:
            next_trigger_local = RemindersUtils._calculate_yearly_trigger(
                base_time_local, recurrence_config, target_time
            )

        else:
            raise ValidationError(f"Unsupported recurrence type: {recurrence_type}")

        # Convert back to UTC for storage
        return to_utc(next_trigger_local, user_timezone)

    async def _schedule_reminder(
        self,
        reminder: Reminder,
        user_timezone: str = "UTC",
    ) -> str:
        """Schedule a reminder with QStash.

        Args:
            scheduler: Scheduler instance
            reminder: Reminder object
            user_timezone: User's timezone

        Returns:
            QStash schedule ID
        """
        webhook_url = f"{config.app_base_url}/reminders/webhook/trigger"
        payload = {
            "reminder_id": reminder.id,
            "user_id": reminder.user_id,
        }

        # Schedule at the next trigger time
        schedule_id = await self.scheduler.schedule_at(
            url=webhook_url,
            payload=payload,
            at=reminder.next_trigger_at,
            retries=3,
        )

        return schedule_id

    async def _cancel_schedule(self, schedule_id: str) -> None:
        """Cancel a scheduled reminder.

        Args:
            scheduler: Scheduler instance
            schedule_id: QStash schedule/message ID to cancel
        """
        try:
            # Try to cancel as a one-time message first
            await self.scheduler.cancel_message(schedule_id)
        except Exception as e:
            # If that fails, might be a recurring schedule (though we use schedule_at)
            logger.debug(f"Failed to cancel as message, trying as schedule: {e}")
            try:
                await self.scheduler.delete_recurring(schedule_id)
            except Exception as e2:
                logger.warning(f"Failed to cancel schedule {schedule_id}: {e2}")
