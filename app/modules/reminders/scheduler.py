from datetime import datetime
from typing import Optional, List
import logging

from pydantic import ValidationError

from app.core.config import config
from app.core.cron.service import CronService, JobScheduleBuilder
from app.core.cron.types import DetailedJob, JobExtendedData, JobSchedule
from app.modules.reminders.models import Reminder
from app.modules.reminders.types import RecurrenceConfig, RecurrenceType

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """Service that manages reminder scheduling using cron-job.org"""

    def __init__(self, cron_service: CronService):
        self.cron_service = cron_service

    # ---------------------------
    # Internal helpers
    # ---------------------------

    def _parse_time(self, time_str: Optional[str]) -> tuple[int, int]:
        """Safely parse 'HH:MM' string to (hour, minute)."""
        if not time_str:
            return 0, 0
        try:
            hour, minute = map(int, time_str.split(":"))
            return hour, minute
        except Exception:
            logger.warning(f"Invalid time format: {time_str}, defaulting to 00:00")
            return 0, 0

    def _convert_to_cron_schedule(
        self,
        recurrence_type: RecurrenceType,
        recurrence_config: Optional[RecurrenceConfig],
        next_trigger_at: datetime,
        user_timezone: str = "UTC",
    ) -> JobSchedule:
        """Convert a reminder recurrence to cron-job.org schedule."""
        hour, minute = self._parse_time(getattr(recurrence_config, "time", None))
        builder = JobScheduleBuilder(timezone=user_timezone)

        try:
            if recurrence_type == RecurrenceType.ONCE:
                return JobScheduleBuilder.once_at(
                    year=next_trigger_at.year,
                    month=next_trigger_at.month,
                    day=next_trigger_at.day,
                    hour=next_trigger_at.hour,
                    minute=next_trigger_at.minute,
                    timezone=user_timezone,
                ).build()

            if recurrence_type == RecurrenceType.DAILY:
                return JobScheduleBuilder.every_day(
                    timezone=user_timezone, at_hour=hour, at_minute=minute
                ).build()

            if recurrence_type == RecurrenceType.WEEKLY:
                if not recurrence_config or not recurrence_config.days:
                    raise ValueError("Weekly recurrence requires 'days'")
                # Convert Python weekdays (0=Mon) → Cron weekdays (0=Sun)
                cron_days = [(d + 1) % 7 for d in recurrence_config.days]
                return (
                    builder.set_wdays(cron_days)
                    .set_hours([hour])
                    .set_minutes([minute])
                    .build()
                )

            if recurrence_type == RecurrenceType.MONTHLY:
                if not recurrence_config or not recurrence_config.day:
                    raise ValueError("Monthly recurrence requires 'day'")
                return JobScheduleBuilder.every_month(
                    timezone=user_timezone,
                    day_of_month=recurrence_config.day,
                    at_hour=hour,
                    at_minute=minute,
                ).build()

            if recurrence_type == RecurrenceType.YEARLY:
                if not recurrence_config or not (
                    recurrence_config.month and recurrence_config.day
                ):
                    raise ValueError("Yearly recurrence requires 'month' and 'day'")
                return (
                    builder.set_months([recurrence_config.month])
                    .set_mdays([recurrence_config.day])
                    .set_hours([hour])
                    .set_minutes([minute])
                    .build()
                )

        except Exception as e:
            logger.error(f"Failed to build schedule: {e}")
            raise

    def _build_job_payload(
        self, reminder: Reminder, schedule: JobSchedule
    ) -> DetailedJob:
        """Assemble the job definition for cron-job.org."""
        webhook_url = f"{config.app_base_url}/reminders/{reminder.id}/process"
        return DetailedJob(
            url=webhook_url,
            title=f"Reminder: {reminder.title}",
            enabled=reminder.is_active,
            schedule=schedule,
            extendedData=JobExtendedData(
                headers={
                    "Content-Type": "application/json",
                    "X-Process-Token": config.reminders_process_token,
                },
            ),
        )

    # ---------------------------
    # Public methods
    # ---------------------------

    async def upsert_cron_job(
        self, reminder: Reminder, user_timezone: str = "UTC"
    ) -> Optional[int]:
        """
        Create or update a cron job for the given reminder.
        Returns the job ID if successful, or None on failure.
        """
        if not self.cron_service:
            logger.warning("CronService not available; skipping job scheduling")
            return None

        try:
            # Build schedule
            schedule = self._convert_to_cron_schedule(
                recurrence_type=RecurrenceType(reminder.recurrence_type),
                recurrence_config=RecurrenceConfig.model_validate(
                    reminder.recurrence_config or {}
                ),
                next_trigger_at=reminder.next_trigger_at,
                user_timezone=user_timezone,
            )

            # Prepare payload
            job_data = self._build_job_payload(reminder, schedule)

            # Create or update
            if reminder.cron_job_id:
                success = await self.cron_service.update_job(
                    reminder.cron_job_id, job_data.model_dump(exclude_none=True)
                )
                if success:
                    logger.info(f"Updated cron job {reminder.cron_job_id}")
                    return reminder.cron_job_id
                logger.error(f"Failed to update cron job {reminder.cron_job_id}")
                return None
            else:
                job_id = await self.cron_service.create_job(job_data)
                if job_id:
                    logger.info(f"Created cron job {job_id} for reminder {reminder.id}")
                    return job_id
                logger.error(f"Failed to create cron job for reminder {reminder.id}")
                return None

        except Exception as e:
            logger.exception(
                f"Error scheduling cron job for reminder {reminder.id}: {e}"
            )
            return None

    async def delete_cron_job(self, cron_job_id: int) -> bool:
        """Delete a cron job by ID."""
        if not self.cron_service:
            logger.warning("CronService not available; skipping job deletion")
            return False

        try:
            success = await self.cron_service.delete_job(cron_job_id)
            if success:
                logger.info(f"Deleted cron job {cron_job_id}")
            else:
                logger.error(f"Failed to delete cron job {cron_job_id}")
            return success
        except Exception as e:
            logger.exception(f"Error deleting cron job {cron_job_id}: {e}")
            return False
