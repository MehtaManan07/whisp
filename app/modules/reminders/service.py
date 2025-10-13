# app/modules/reminders/service.py

from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select
from dateutil.relativedelta import relativedelta

from app.modules.reminders.models import Reminder
from app.modules.reminders.types import ReminderType, RecurrenceType, RecurrenceConfig
from app.modules.reminders.dto import CreateReminderDTO, UpdateReminderDTO, ListRemindersDTO
from app.core.exceptions import NotFoundError, ValidationError
from app.utils.datetime import utc_now


class ReminderService:
    """Service for managing reminders."""

    async def create_reminder(self, db: AsyncSession, user_id: int, data: CreateReminderDTO) -> Reminder:
        """Create a new reminder."""
        # Validate recurrence config
        if data.recurrence_type != RecurrenceType.ONCE and not data.recurrence_config:
            raise ValidationError("Recurrence config required for recurring reminders")

        try:
            # Calculate initial trigger time
            next_trigger = self._calculate_next_trigger(
                base_time=data.next_trigger_at or utc_now(),
                recurrence_type=data.recurrence_type,
                recurrence_config=data.recurrence_config,
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

    async def get_reminder(self, db: AsyncSession, reminder_id: int, user_id: int) -> Reminder:
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
            raise NotFoundError(f"Reminder {reminder_id} not found", resource_id=str(reminder_id))

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
            select(Reminder)
            .where(and_(*conditions))
            .order_by(Reminder.next_trigger_at)
        )
        return list(result.scalars().all())

    async def update_reminder(
        self, db: AsyncSession, reminder_id: int, user_id: int, data: UpdateReminderDTO
    ) -> Reminder:
        """Update an existing reminder."""
        reminder = await self.get_reminder(db, reminder_id, user_id)

        try:
            # Update fields
            if data.title is not None:
                reminder.title = data.title
            if data.description is not None:
                reminder.description = data.description
            if data.amount is not None:
                reminder.amount = data.amount
            if data.category_id is not None:
                reminder.category_id = data.category_id
            if data.is_active is not None:
                reminder.is_active = data.is_active

            # Update recurrence if changed
            if data.recurrence_type or data.recurrence_config:
                recurrence_type = data.recurrence_type or RecurrenceType(reminder.recurrence_type)
                recurrence_config = data.recurrence_config or reminder.recurrence_config

                reminder.recurrence_type = recurrence_type
                reminder.recurrence_config = (
                    recurrence_config.dict()
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
                )

            await db.commit()
            await db.refresh(reminder)
            
            return reminder
            
        except Exception as e:
            await db.rollback()
            raise

    async def delete_reminder(self, db: AsyncSession, reminder_id: int, user_id: int) -> None:
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

    async def complete_reminder(self, db: AsyncSession, reminder_id: int, user_id: int) -> Reminder:
        """Mark a reminder as completed."""
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

    async def get_due_reminders(self, db: AsyncSession, limit: int = 100) -> List[Reminder]:
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

    async def process_triggered_reminder(self, db: AsyncSession, reminder: Reminder) -> None:
        """Process a reminder after it has been triggered."""
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
    ) -> datetime:
        """Calculate the next trigger time based on recurrence pattern (always UTC)."""
        # Parse time from config
        target_time = self._parse_target_time(recurrence_config)

        if recurrence_type == RecurrenceType.ONCE:
            return base_time

        elif recurrence_type == RecurrenceType.DAILY:
            next_trigger = self._calculate_daily_trigger(base_time, target_time)

        elif recurrence_type == RecurrenceType.WEEKLY:
            next_trigger = self._calculate_weekly_trigger(
                base_time, recurrence_config, target_time
            )

        elif recurrence_type == RecurrenceType.MONTHLY:
            next_trigger = self._calculate_monthly_trigger(
                base_time, recurrence_config, target_time
            )

        elif recurrence_type == RecurrenceType.YEARLY:
            next_trigger = self._calculate_yearly_trigger(
                base_time, recurrence_config, target_time
            )

        else:
            raise ValidationError(f"Unsupported recurrence type: {recurrence_type}")

        return next_trigger
    
    def _parse_target_time(self, recurrence_config: Optional[RecurrenceConfig]) -> Optional[Tuple[int, int]]:
        """Parse target time from recurrence config."""
        if recurrence_config and recurrence_config.time:
            try:
                hours, minutes = map(int, recurrence_config.time.split(":"))
                if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                    raise ValidationError(f"Invalid time format: {recurrence_config.time}")
                return (hours, minutes)
            except ValueError:
                raise ValidationError(f"Invalid time format: {recurrence_config.time}")
        return None
    
    def _apply_target_time(self, dt: datetime, target_time: Optional[Tuple[int, int]]) -> datetime:
        """Apply target time to a datetime object."""
        if target_time:
            return dt.replace(
                hour=target_time[0], minute=target_time[1], second=0, microsecond=0
            )
        return dt
    
    def _calculate_daily_trigger(
        self, base_time: datetime, target_time: Optional[Tuple[int, int]]
    ) -> datetime:
        """Calculate next trigger for daily recurrence."""
        next_trigger = base_time + timedelta(days=1)
        return self._apply_target_time(next_trigger, target_time)
    
    def _calculate_weekly_trigger(
        self,
        base_time: datetime,
        recurrence_config: Optional[RecurrenceConfig],
        target_time: Optional[Tuple[int, int]],
    ) -> datetime:
        """Calculate next trigger for weekly recurrence."""
        if not recurrence_config or not recurrence_config.days:
            raise ValidationError("Weekly recurrence requires 'days' in config")

        current_day = base_time.weekday()
        target_days = sorted(recurrence_config.days)

        # Find next day in the cycle
        next_day = None
        for day in target_days:
            if day > current_day:
                next_day = day
                break

        if next_day is None:
            # Wrap to next week
            next_day = target_days[0]
            days_ahead = (7 - current_day) + next_day
        else:
            days_ahead = next_day - current_day

        next_trigger = base_time + timedelta(days=days_ahead)
        return self._apply_target_time(next_trigger, target_time)
    
    def _calculate_monthly_trigger(
        self,
        base_time: datetime,
        recurrence_config: Optional[RecurrenceConfig],
        target_time: Optional[Tuple[int, int]],
    ) -> datetime:
        """Calculate next trigger for monthly recurrence."""
        if not recurrence_config or not recurrence_config.day:
            raise ValidationError("Monthly recurrence requires 'day' in config")

        target_day = recurrence_config.day
        next_trigger = base_time + relativedelta(months=1)

        # Handle month-end edge cases
        try:
            next_trigger = next_trigger.replace(day=target_day)
        except ValueError:
            # Day doesn't exist in month (e.g., Feb 30), use last day
            next_trigger = (
                next_trigger.replace(day=1)
                + relativedelta(months=1)
                - timedelta(days=1)
            )

        return self._apply_target_time(next_trigger, target_time)
    
    def _calculate_yearly_trigger(
        self,
        base_time: datetime,
        recurrence_config: Optional[RecurrenceConfig],
        target_time: Optional[Tuple[int, int]],
    ) -> datetime:
        """Calculate next trigger for yearly recurrence."""
        if (
            not recurrence_config
            or not recurrence_config.month
            or not recurrence_config.day
        ):
            raise ValidationError(
                "Yearly recurrence requires 'month' and 'day' in config"
            )

        next_trigger = base_time + relativedelta(years=1)
        next_trigger = next_trigger.replace(
            month=recurrence_config.month, day=recurrence_config.day
        )

        return self._apply_target_time(next_trigger, target_time)
