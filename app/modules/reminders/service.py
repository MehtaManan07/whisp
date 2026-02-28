from datetime import timedelta
from typing import Any, List, Optional, TYPE_CHECKING
from sqlalchemy.orm import Session
from sqlalchemy import and_, select
import logging

from app.modules.reminders.models import Reminder

if TYPE_CHECKING:
    from app.integrations.whatsapp.service import WhatsAppService
    from app.modules.users.service import UsersService
from app.modules.reminders.types import RecurrenceType, RecurrenceConfig
from app.modules.reminders.dto import (
    CreateReminderDTO,
    UpdateReminderDTO,
    ListRemindersDTO,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.modules.reminders.utils import RemindersUtils
from app.utils.datetime import utc_now
from app.core.db.engine import run_db

logger = logging.getLogger(__name__)


class ReminderService:
    """Service for managing reminders."""

    def __init__(self):
        self.logger = logger

    # -------------------------------------------------------------------------
    # Sync helpers
    # -------------------------------------------------------------------------

    def get_reminder_sync(self, db: Session, reminder_id: int, user_id: int) -> Reminder:
        result = db.execute(
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

    def process_triggered_reminder_sync(
        self,
        db: Session,
        reminder: Reminder,
        user_timezone: str = "UTC",
    ) -> None:
        """Process a reminder after it has been triggered (sync)."""
        try:
            reminder.last_triggered_at = utc_now()

            if reminder.is_recurring:
                reminder.next_trigger_at = RemindersUtils.calculate_next_trigger(
                    base_time=utc_now(),
                    recurrence_type=RecurrenceType(reminder.recurrence_type),
                    recurrence_config=(
                        RecurrenceConfig.model_validate(reminder.recurrence_config)
                        if reminder.recurrence_config
                        else None
                    ),
                    user_timezone=user_timezone,
                )
                logger.info(
                    f"Updated recurring reminder {reminder.id} to next trigger at {reminder.next_trigger_at}"
                )
            else:
                reminder.is_active = False
                logger.info(f"Deactivated one-time reminder {reminder.id}")

            db.commit()

        except Exception as e:
            db.rollback()
            raise

    # -------------------------------------------------------------------------
    # Async public API
    # -------------------------------------------------------------------------

    async def create_reminder(
        self,
        user_id: int,
        data: CreateReminderDTO,
        user_timezone: str = "UTC",
    ) -> Reminder:
        """Create a new reminder."""
        if data.recurrence_type != RecurrenceType.ONCE and not data.recurrence_config:
            raise ValidationError("Recurrence config required for recurring reminders")

        def _create(db: Session) -> Reminder:
            try:
                next_trigger = RemindersUtils.calculate_next_trigger(
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
                db.commit()
                db.refresh(reminder)

                logger.info(f"Created reminder {reminder.id}")
                return reminder

            except Exception:
                db.rollback()
                raise

        return await run_db(_create)

    async def get_reminder(
        self, reminder_id: int, user_id: int
    ) -> Reminder:
        return await run_db(lambda db: self.get_reminder_sync(db, reminder_id, user_id))

    async def list_reminders(
        self,
        data: ListRemindersDTO,
    ) -> List[Reminder]:
        def _list(db: Session) -> List[Reminder]:
            conditions = [Reminder.user_id == data.user_id, Reminder.deleted_at.is_(None)]

            if data.reminder_type:
                conditions.append(Reminder.reminder_type == data.reminder_type)

            if data.is_active is not None:
                conditions.append(Reminder.is_active == data.is_active)

            result = db.execute(
                select(Reminder).where(and_(*conditions)).order_by(Reminder.next_trigger_at)
            )
            return list(result.scalars().all())

        return await run_db(_list)

    async def update_reminder(
        self,
        reminder_id: int,
        user_id: int,
        data: UpdateReminderDTO,
        user_timezone: str = "UTC",
    ) -> Reminder:
        def _update(db: Session) -> Reminder:
            reminder = self.get_reminder_sync(db, reminder_id, user_id)

            try:
                update_data = data.model_dump(
                    exclude_unset=True, exclude={"recurrence_type", "recurrence_config"}
                )
                for field, value in update_data.items():
                    setattr(reminder, field, value)

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

                    reminder.next_trigger_at = RemindersUtils.calculate_next_trigger(
                        base_time=utc_now(),
                        recurrence_type=recurrence_type,
                        recurrence_config=(
                            RecurrenceConfig.model_validate(reminder.recurrence_config)
                            if reminder.recurrence_config
                            else None
                        ),
                        user_timezone=user_timezone,
                    )

                db.commit()
                db.refresh(reminder)
                return reminder

            except Exception as e:
                db.rollback()
                raise

        return await run_db(_update)

    async def delete_reminder(
        self,
        reminder_id: int,
        user_id: int,
    ) -> None:
        def _delete(db: Session) -> None:
            reminder = self.get_reminder_sync(db, reminder_id, user_id)

            try:
                reminder.deleted_at = utc_now()
                reminder.is_active = False
                db.commit()
                logger.info(f"Deleted reminder {reminder_id}")

            except Exception as e:
                db.rollback()
                raise

        await run_db(_delete)

    async def snooze_reminder(
        self, reminder_id: int, user_id: int, duration: timedelta
    ) -> Reminder:
        def _snooze(db: Session) -> Reminder:
            reminder = self.get_reminder_sync(db, reminder_id, user_id)
            reminder.next_trigger_at = utc_now() + duration

            try:
                db.commit()
                db.refresh(reminder)
                return reminder
            except Exception as e:
                db.rollback()
                raise

        return await run_db(_snooze)

    async def complete_reminder(
        self,
        reminder_id: int,
        user_id: int,
        user_timezone: str = "UTC",
    ) -> Reminder:
        def _complete(db: Session) -> Reminder:
            reminder = self.get_reminder_sync(db, reminder_id, user_id)

            try:
                if reminder.is_recurring:
                    reminder.last_triggered_at = utc_now()
                    reminder.next_trigger_at = RemindersUtils.calculate_next_trigger(
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
                    reminder.is_active = False
                    reminder.last_triggered_at = utc_now()

                db.commit()
                db.refresh(reminder)
                return reminder

            except Exception as e:
                db.rollback()
                raise

        return await run_db(_complete)

    async def get_due_reminders(
        self, limit: int = 100
    ) -> List[Reminder]:
        def _get(db: Session) -> List[Reminder]:
            result = db.execute(
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

        return await run_db(_get)

    async def fix_overdue_reminders(
        self,
        user_id: Optional[int] = None,
        user_timezone: str = "UTC",
    ) -> int:
        def _fix(db: Session) -> int:
            try:
                conditions = [
                    Reminder.is_active == True,
                    Reminder.deleted_at.is_(None),
                    Reminder.recurrence_type != "once",
                ]

                if user_id:
                    conditions.append(Reminder.user_id == user_id)

                result = db.execute(select(Reminder).where(and_(*conditions)))
                overdue_reminders = list(result.scalars().all())

                fixed_count = 0

                for reminder in overdue_reminders:
                    reminder.next_trigger_at = RemindersUtils.calculate_next_trigger(
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

                db.commit()
                return fixed_count

            except Exception as e:
                db.rollback()
                raise

        return await run_db(_fix)

    async def process_triggered_reminder(
        self,
        reminder: Reminder,
        user_timezone: str = "UTC",
    ) -> None:
        """Process a reminder after it has been triggered."""
        def _process(db: Session) -> None:
            # Re-fetch reminder in this session
            fresh = db.get(Reminder, reminder.id)
            if fresh:
                self.process_triggered_reminder_sync(db, fresh, user_timezone)

        await run_db(_process)

    async def process_single_reminder(
        self,
        reminder_id: int,
        user_service: "UsersService",
        whatsapp_service: "WhatsAppService",
    ) -> dict[str, Any]:
        """
        Process a specific reminder by ID (called by scheduled cron jobs).
        """
        try:
            # Fetch reminder and user info in one DB call
            def _fetch(db: Session):
                result = db.execute(
                    select(Reminder).where(
                        and_(
                            Reminder.id == reminder_id,
                            Reminder.is_active == True,
                            Reminder.deleted_at.is_(None),
                        )
                    )
                )
                return result.scalar_one_or_none()

            reminder = await run_db(_fetch)

            if not reminder:
                logger.warning(f"Reminder {reminder_id} not found or not active")
                return {
                    "status": "error",
                    "message": f"Reminder {reminder_id} not found or not active",
                    "processed": 0,
                }

            user = await user_service.get_user_by_id(reminder.user_id)
            if not user or not user.phone_number:
                logger.error(f"User {reminder.user_id} not found or has no phone number")
                return {
                    "status": "error",
                    "message": f"User {reminder.user_id} not found or has no phone number",
                    "processed": 0,
                }

            user_timezone = user_service.get_user_timezone(user) if user else "UTC"

            # Send WhatsApp notification
            try:
                message = f"🔔 Reminder: {reminder.title}"
                if reminder.amount:
                    message += f"\nAmount: ₹{reminder.amount:,.2f}"
                if reminder.description:
                    message += f"\n\n{reminder.description}"

                await whatsapp_service.send_text(user.phone_number, message)
                logger.info(f"Sent reminder {reminder.id} to user {user.phone_number}")
            except Exception as e:
                logger.error(
                    f"Failed to send WhatsApp notification for reminder {reminder.id}: {e}"
                )
                return {
                    "status": "error",
                    "message": f"Failed to send notification: {str(e)}",
                    "processed": 0,
                }

            # Mark as triggered
            await self.process_triggered_reminder(reminder, user_timezone)

            logger.info(f"Successfully processed reminder {reminder_id}")
            return {
                "status": "success",
                "processed": 1,
                "reminder_id": reminder_id,
                "message": f"Successfully processed reminder {reminder_id}",
            }

        except Exception as e:
            logger.error(f"Error processing reminder {reminder_id}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "processed": 0,
            }
