# app/core/scheduler/scheduler.py

import logging
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from qstash import AsyncQStash
from qstash.http import HttpMethod
from qstash.schedule import Schedule  # if needed

from app.core.config import config
from app.core.exceptions import SchedulerError, ValidationError
from app.utils.datetime import utc_now

logger = logging.getLogger(__name__)


class Scheduler:
    """Scheduler for delayed and recurring jobs using QStash."""

    def __init__(self):
        if not config.qstash_token:
            raise ValueError("QSTASH_TOKEN is required")
        self._client = AsyncQStash(config.qstash_token)

    async def schedule_in(
        self,
        url: str,
        payload: Dict[str, Any],
        seconds: int,
        retries: int = 3,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[str] = None,
        method: Optional[HttpMethod] = "POST",
    ) -> str:
        """Schedule a one-time job after N seconds delay."""
        if seconds < 0:
            raise ValidationError("Delay (seconds) must be non-negative")
        delay_str = f"{seconds}s"
        try:
            resp = await self._client.message.publish_json(
                url=url,
                body=payload,
                delay=delay_str,
                retries=retries,
                headers=headers,
                timeout=timeout,
                method=method,
            )
            message_id = getattr(resp, "message_id", None)
            logger.info(
                f"Scheduled message (id={message_id}) to run in {seconds}s at {url}"
            )
            return str(message_id)
        except Exception as e:
            logger.error(f"Failed to schedule job (delay={seconds}s url={url}): {e}")
            raise SchedulerError(f"Failed to schedule job: {e}")

    async def schedule_at(
        self,
        url: str,
        payload: Dict[str, Any],
        at: datetime,
        retries: int = 3,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[str] = None,
        method: Optional[HttpMethod] = "POST",
    ) -> str:
        """Schedule a one-time job at a specific UTC datetime."""
        now = utc_now()
        if at <= now:
            raise ValidationError("Schedule time must be in the future")
        if at.tzinfo is None:
            raise ValidationError("Datetime must be timezone-aware (UTC)")

        seconds = int((at - now).total_seconds())
        return await self.schedule_in(
            url=url,
            payload=payload,
            seconds=seconds,
            retries=retries,
            headers=headers,
            timeout=timeout,
            method=method,
        )

    async def create_recurring(
        self,
        url: str,
        cron: str,
        payload: Optional[Dict[str, Any]] = None,
        retries: int = 3,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[str] = None,
        method: Optional[HttpMethod] = "POST",
    ) -> str:
        """Create a recurring job using cron expression."""
        try:
            body = json.dumps(payload) if payload is not None else None
            resp = await self._client.schedule.create(
                destination=url,
                cron=cron,
                body=body,
                retries=retries,
                headers=headers,
                timeout=timeout,
                method=method,
            )
            schedule_id = getattr(resp, "schedule_id", None)
            logger.info(
                f"Created recurring schedule (id={schedule_id}) cron={cron} → {url}"
            )
            return str(schedule_id)
        except Exception as e:
            logger.error(
                f"Failed to create recurring schedule (cron={cron} url={url}): {e}"
            )
            raise SchedulerError(f"Failed to create recurring schedule: {e}")

    async def delete_recurring(self, schedule_id: str) -> None:
        """Delete a recurring schedule by ID."""
        try:
            await self._client.schedule.delete(schedule_id)
            logger.info(f"Deleted schedule id={schedule_id}")
        except Exception as e:
            logger.error(f"Failed to delete schedule id={schedule_id}: {e}")
            raise SchedulerError(f"Failed to delete schedule: {e}")

    async def pause(self, schedule_id: str) -> None:
        """Pause a recurring schedule."""
        try:
            await self._client.schedule.pause(schedule_id)
            logger.info(f"Paused schedule id={schedule_id}")
        except Exception as e:
            logger.error(f"Failed to pause schedule id={schedule_id}: {e}")
            raise SchedulerError(f"Failed to pause schedule: {e}")

    async def resume(self, schedule_id: str) -> None:
        """Resume a paused recurring schedule."""
        try:
            await self._client.schedule.resume(schedule_id)
            logger.info(f"Resumed schedule id={schedule_id}")
        except Exception as e:
            logger.error(f"Failed to resume schedule id={schedule_id}: {e}")
            raise SchedulerError(f"Failed to resume schedule: {e}")

    async def cancel_message(self, message_id: str) -> None:
        """Cancel a scheduled one-time message by ID."""
        try:
            await self._client.message.cancel(message_id)
            logger.info(f"Cancelled message id={message_id}")
        except Exception as e:
            logger.error(f"Failed to cancel message id={message_id}: {e}")
            raise SchedulerError(f"Failed to cancel message: {e}")

    async def get_schedule(self, schedule_id: str) -> Schedule:
        """Retrieve details of a recurring schedule."""
        try:
            resp = await self._client.schedule.get(schedule_id)
            return resp
        except Exception as e:
            logger.error(f"Failed to get schedule id={schedule_id}: {e}")
            raise SchedulerError(f"Failed to get schedule: {e}")

    async def list_schedules(self) -> List[Schedule]:
        """List all recurring schedules."""
        try:
            resp = await self._client.schedule.list()
            return resp
        except Exception as e:
            logger.error(f"Failed to list schedules: {e}")
            raise SchedulerError(f"Failed to list schedules: {e}")


class Cron:
    """Cron expression builder helpers."""

    @staticmethod
    def every_n_minutes(n: int) -> str:
        if not (1 <= n <= 59):
            raise ValidationError("Minutes must be between 1 and 59")
        return f"*/{n} * * * *"

    @staticmethod
    def every_n_hours(n: int) -> str:
        if not (1 <= n <= 23):
            raise ValidationError("Hours must be between 1 and 23")
        return f"0 */{n} * * *"

    @staticmethod
    def daily_at(hour: int, minute: int = 0) -> str:
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValidationError("Invalid hour/minute")
        return f"{minute} {hour} * * *"

    @staticmethod
    def weekly(day: int, hour: int = 9, minute: int = 0) -> str:
        if not (0 <= day <= 6 and 0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValidationError("Invalid values for weekly schedule")
        return f"{minute} {hour} * * {day}"

    @staticmethod
    def monthly(day: int, hour: int = 9, minute: int = 0) -> str:
        if not (1 <= day <= 31 and 0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValidationError("Invalid values for monthly schedule")
        return f"{minute} {hour} {day} * *"
