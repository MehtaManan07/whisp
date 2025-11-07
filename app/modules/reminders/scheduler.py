from datetime import datetime
from typing import Optional

from pydantic import ValidationError
from app.core.cron.service import CronService, JobScheduleBuilder
from app.core.cron.types import DetailedJob, JobExtendedData, JobSchedule, RequestMethod
from app.modules.reminders.models import Reminder
from app.modules.reminders.types import RecurrenceConfig, RecurrenceType
import logging
from app.core.config import config

logger = logging.getLogger(__name__)


class ReminderScheduler:
    def __init__(self, cron_service: CronService):
        self.cron_service = cron_service

    def _convert_to_cron_schedule(
        self,
        recurrence_type: RecurrenceType,
        recurrence_config: Optional[RecurrenceConfig],
        next_trigger_at: datetime,
        user_timezone: str = "UTC",
    ) -> JobSchedule:
        """
        Convert reminder recurrence pattern to cron schedule.

        Args:
            recurrence_type: Type of recurrence (once, daily, weekly, monthly, yearly)
            recurrence_config: Configuration for the recurrence
            next_trigger_at: Next trigger time (used for one-time reminders)
            user_timezone: User's timezone

        Returns:
            Cron schedule dictionary
        """
        # Parse target time from recurrence config
        target_hour = 0
        target_minute = 0

        if recurrence_config and recurrence_config.time:
            try:
                time_parts = recurrence_config.time.split(":")
                target_hour = int(time_parts[0])
                target_minute = int(time_parts[1])
            except (ValueError, IndexError):
                logger.warning(f"Invalid time format: {recurrence_config.time}")

        # Build cron schedule based on recurrence type
        if recurrence_type == RecurrenceType.ONCE:
            # For one-time reminders, use once_at builder
            return JobScheduleBuilder.once_at(
                year=next_trigger_at.year,
                month=next_trigger_at.month,
                day=next_trigger_at.day,
                hour=next_trigger_at.hour,
                minute=next_trigger_at.minute,
                timezone=user_timezone,
            ).build()

        elif recurrence_type == RecurrenceType.DAILY:
            # Run daily at the specified time
            return JobScheduleBuilder.every_day(
                timezone=user_timezone,
                at_hour=target_hour,
                at_minute=target_minute,
            ).build()

        elif recurrence_type == RecurrenceType.WEEKLY:
            # Run weekly on specified days
            if not recurrence_config or not recurrence_config.days:
                raise ValidationError("Weekly recurrence requires 'days' in config")

            # Convert Python weekday (0=Monday) to cron weekday (0=Sunday)
            # Python: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
            # Cron: 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat
            cron_days = [(day + 1) % 7 for day in recurrence_config.days]

            builder = JobScheduleBuilder(timezone=user_timezone)
            builder.set_wdays(cron_days)
            builder.set_hours([target_hour])
            builder.set_minutes([target_minute])
            return builder.build()

        elif recurrence_type == RecurrenceType.MONTHLY:
            # Run monthly on specified day
            if not recurrence_config or not recurrence_config.day:
                raise ValidationError("Monthly recurrence requires 'day' in config")

            return JobScheduleBuilder.every_month(
                timezone=user_timezone,
                day_of_month=recurrence_config.day,
                at_hour=target_hour,
                at_minute=target_minute,
            ).build()

        elif recurrence_type == RecurrenceType.YEARLY:
            # Run yearly on specified month and day
            if (
                not recurrence_config
                or not recurrence_config.month
                or not recurrence_config.day
            ):
                raise ValidationError(
                    "Yearly recurrence requires 'month' and 'day' in config"
                )

            builder = JobScheduleBuilder(timezone=user_timezone)
            builder.set_months([recurrence_config.month])
            builder.set_mdays([recurrence_config.day])
            builder.set_hours([target_hour])
            builder.set_minutes([target_minute])
            return builder.build()

        else:
            raise ValidationError(f"Unsupported recurrence type: {recurrence_type}")

    async def schedule_cron_job(
        self,
        reminder: Reminder,
        user_timezone: str = "UTC",
    ) -> Optional[int]:
        """
        Schedule a cron job for a reminder.

        Args:
            reminder: Reminder object
            user_timezone: User's timezone

        Returns:
            Cron job ID or None if scheduling failed
        """
        if not self.cron_service:
            logger.warning("CronService not available, skipping cron job scheduling")
            return None

        try:
            # Build the webhook URL for the process endpoint
            webhook_url = f"{config.app_base_url}/reminders/process"

            # Convert reminder schedule to cron schedule
            schedule = self._convert_to_cron_schedule(
                recurrence_type=RecurrenceType(reminder.recurrence_type),
                recurrence_config=(
                    RecurrenceConfig.model_validate(reminder.recurrence_config)
                    if reminder.recurrence_config
                    else None
                ),
                next_trigger_at=reminder.next_trigger_at,
                user_timezone=user_timezone,
            )

            # Create the cron job
            job_data = DetailedJob(
                url=webhook_url,
                title=f"Reminder: {reminder.title}",
                enabled=reminder.is_active,
                schedule=schedule,
                extendedData=JobExtendedData(
                    headers={
                        "X-Process-Token": config.reminders_process_token,
                        "Content-Type": "application/json",
                    },
                ),
            )

            job_id = await self.cron_service.create_job(job_data)

            if job_id:
                logger.info(f"Created cron job {job_id} for reminder {reminder.id}")
            else:
                logger.error(f"Failed to create cron job for reminder {reminder.id}")

            return job_id

        except Exception as e:
            logger.error(f"Error scheduling cron job for reminder {reminder.id}: {e}")
            return None

    async def update_cron_job(
        self,
        reminder: Reminder,
        user_timezone: str = "UTC",
    ) -> bool:
        """
        Update an existing cron job for a reminder.

        Args:
            reminder: Reminder object with cron_job_id
            user_timezone: User's timezone

        Returns:
            True if update succeeded, False otherwise
        """
        if not self.cron_service or not reminder.cron_job_id:
            logger.warning(
                "CronService not available or no cron_job_id, skipping update"
            )
            return False

        try:
            # Convert reminder schedule to cron schedule
            schedule = self._convert_to_cron_schedule(
                recurrence_type=RecurrenceType(reminder.recurrence_type),
                recurrence_config=(
                    RecurrenceConfig.model_validate(reminder.recurrence_config)
                    if reminder.recurrence_config
                    else None
                ),
                next_trigger_at=reminder.next_trigger_at,
                user_timezone=user_timezone,
            )

            # Update the cron job
            job_data = {
                "title": f"Reminder: {reminder.title}",
                "enabled": reminder.is_active,
                "schedule": schedule,
            }

            success = await self.cron_service.update_job(reminder.cron_job_id, job_data)

            if success:
                logger.info(
                    f"Updated cron job {reminder.cron_job_id} for reminder {reminder.id}"
                )
            else:
                logger.error(
                    f"Failed to update cron job {reminder.cron_job_id} for reminder {reminder.id}"
                )

            return success

        except Exception as e:
            logger.error(f"Error updating cron job for reminder {reminder.id}: {e}")
            return False

    async def delete_cron_job(self, cron_job_id: int) -> bool:
        """
        Delete a cron job.

        Args:
            cron_job_id: Cron job ID

        Returns:
            True if deletion succeeded, False otherwise
        """
        if not self.cron_service:
            logger.warning("CronService not available, skipping cron job deletion")
            return False

        try:
            success = await self.cron_service.delete_job(cron_job_id)

            if success:
                logger.info(f"Deleted cron job {cron_job_id}")
            else:
                logger.error(f"Failed to delete cron job {cron_job_id}")

            return success

        except Exception as e:
            logger.error(f"Error deleting cron job {cron_job_id}: {e}")
            return False
