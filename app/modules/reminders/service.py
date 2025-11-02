# app/modules/reminders/service.py

from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select

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


class ReminderService:
    """Service for managing reminders."""

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

        try:
            # Update simple fields efficiently using model_dump
            update_data = data.model_dump(
                exclude_unset=True, exclude={"recurrence_type", "recurrence_config"}
            )
            for field, value in update_data.items():
                setattr(reminder, field, value)

            # Update recurrence if changed
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

            await db.commit()
            await db.refresh(reminder)

            return reminder

        except Exception as e:
            await db.rollback()
            raise

    async def delete_reminder(
        self, db: AsyncSession, reminder_id: int, user_id: int
    ) -> None:
        """Soft delete a reminder by marking deleted_at."""
        reminder = await self.get_reminder(db, reminder_id, user_id)

        try:
            reminder.deleted_at = utc_now()
            await db.commit()
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

    async def process_triggered_reminder(
        self, db: AsyncSession, reminder: Reminder, user_timezone: str = "UTC"
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
            else:
                # One-time reminder - deactivate
                reminder.is_active = False

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
