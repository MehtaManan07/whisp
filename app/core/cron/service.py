import logging
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar, Union, overload

import httpx
from pydantic import BaseModel, ValidationError

from app.integrations.llm.key_manager import APIKeyManager
from app.core.cron.types import (
    CreateJobResponse,
    DeleteJobResponse,
    Job,
    DetailedJob,
    JobsListResponse,
    UpdateJobResponse,
)
from app.core.fetcher import fetch


logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class JobScheduleBuilder:
    """Helper for building JobSchedule objects with fluent API."""

    def __init__(
        self,
        timezone: str = "UTC",
        expires_at: int = 0,
        hours: Optional[List[int]] = None,
        mdays: Optional[List[int]] = None,
        minutes: Optional[List[int]] = None,
        months: Optional[List[int]] = None,
        wdays: Optional[List[int]] = None,
    ):
        self.timezone = timezone
        self.expires_at = expires_at
        self.hours = hours or []
        self.mdays = mdays or []
        self.minutes = minutes or []
        self.months = months or []
        self.wdays = wdays or []

    @classmethod
    def every_hour(cls, timezone: str = "UTC") -> "JobScheduleBuilder":
        """Execute every hour."""
        return cls(timezone=timezone, minutes=[0])

    @classmethod
    def every_minute(cls, timezone: str = "UTC") -> "JobScheduleBuilder":
        """Execute every minute."""
        return cls(timezone=timezone, minutes=[-1])

    @classmethod
    def every_day(
        cls, timezone: str = "UTC", at_hour: int = 0, at_minute: int = 0
    ) -> "JobScheduleBuilder":
        """Execute every day at specified time."""
        return cls(timezone=timezone, hours=[at_hour], minutes=[at_minute])

    @classmethod
    def every_week(
        cls,
        timezone: str = "UTC",
        day_of_week: int = 0,
        at_hour: int = 0,
        at_minute: int = 0,
    ) -> "JobScheduleBuilder":
        """Execute every week on specified day (0=Sunday - 6=Saturday)."""
        if not 0 <= day_of_week <= 6:
            raise ValueError("day_of_week must be 0-6 (0=Sunday)")
        return cls(
            timezone=timezone, wdays=[day_of_week], hours=[at_hour], minutes=[at_minute]
        )

    @classmethod
    def every_month(
        cls,
        timezone: str = "UTC",
        day_of_month: int = 1,
        at_hour: int = 0,
        at_minute: int = 0,
    ) -> "JobScheduleBuilder":
        """Execute every month on specified day (1-31)."""
        if not 1 <= day_of_month <= 31:
            raise ValueError("day_of_month must be 1-31")
        return cls(
            timezone=timezone,
            mdays=[day_of_month],
            hours=[at_hour],
            minutes=[at_minute],
            months=[-1],
        )

    @classmethod
    def once_at(
        cls,
        year: int,
        month: int,
        day: int,
        hour: int = 0,
        minute: int = 0,
        timezone: str = "UTC",
    ) -> "JobScheduleBuilder":
        """Execute once at specified date and time.

        Args:
            year: Year (YYYY)
            month: Month (1-12)
            day: Day of month (1-31)
            hour: Hour (0-23)
            minute: Minute (0-59)
            timezone: Timezone string

        Returns:
            JobScheduleBuilder configured for one-time execution
        """
        if not 1 <= month <= 12:
            raise ValueError("month must be 1-12")
        if not 1 <= day <= 31:
            raise ValueError("day must be 1-31")
        if not 0 <= hour <= 23:
            raise ValueError("hour must be 0-23")
        if not 0 <= minute <= 59:
            raise ValueError("minute must be 0-59")

        # Format: YYYYMMDDhhmmss
        expires_at = int(f"{year:04d}{month:02d}{day:02d}{hour:02d}{minute:02d}00")

        return cls(
            timezone=timezone,
            expires_at=expires_at,
            hours=[hour],
            mdays=[day],
            minutes=[minute],
            months=[month],
            wdays=[-1],
        )

    def set_timezone(self, timezone: str) -> "JobScheduleBuilder":
        """Set timezone."""
        self.timezone = timezone
        return self

    def set_expires_at(self, expires_at: int) -> "JobScheduleBuilder":
        """Set expiration date/time (format: YYYYMMDDhhmmss, 0 = does not expire)."""
        self.expires_at = expires_at
        return self

    def set_hours(self, hours: List[int]) -> "JobScheduleBuilder":
        """Set hours (0-23; [-1] = every hour)."""
        if hours and not all(h == -1 or 0 <= h <= 23 for h in hours):
            raise ValueError("hours must be -1 or 0-23")
        self.hours = hours
        return self

    def set_minutes(self, minutes: List[int]) -> "JobScheduleBuilder":
        """Set minutes (0-59; [-1] = every minute)."""
        if minutes and not all(m == -1 or 0 <= m <= 59 for m in minutes):
            raise ValueError("minutes must be -1 or 0-59")
        self.minutes = minutes
        return self

    def set_mdays(self, mdays: List[int]) -> "JobScheduleBuilder":
        """Set days of month (1-31; [-1] = every day)."""
        if mdays and not all(d == -1 or 1 <= d <= 31 for d in mdays):
            raise ValueError("mdays must be -1 or 1-31")
        self.mdays = mdays
        return self

    def set_months(self, months: List[int]) -> "JobScheduleBuilder":
        """Set months (1-12; [-1] = every month)."""
        if months and not all(m == -1 or 1 <= m <= 12 for m in months):
            raise ValueError("months must be -1 or 1-12")
        self.months = months
        return self

    def set_wdays(self, wdays: List[int]) -> "JobScheduleBuilder":
        """Set days of week (0=Sunday - 6=Saturday; [-1] = every day)."""
        if wdays and not all(w == -1 or 0 <= w <= 6 for w in wdays):
            raise ValueError("wdays must be -1 or 0-6")
        self.wdays = wdays
        return self

    def build(self) -> Dict[str, Any]:
        """Build the schedule dictionary."""
        return {
            "timezone": self.timezone,
            "expiresAt": self.expires_at,
            "hours": self.hours,
            "mdays": self.mdays,
            "minutes": self.minutes,
            "months": self.months,
            "wdays": self.wdays,
        }


class CronService:
    """Service for interacting with cron-job.org API asynchronously."""

    DEFAULT_TIMEOUT = 10.0
    DEFAULT_HEADERS = {"Content-Type": "application/json"}

    def __init__(
        self,
        api_key_manager: APIKeyManager,
        base_url: str = "https://api.cron-job.org/jobs",
    ):
        self.api_key_manager = api_key_manager
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    def _get_headers(self) -> Dict[str, str]:
        api_key_response = self.api_key_manager.get_available_key()
        if api_key_response is None:
            raise ValueError("No API key available")
        api_key, key_index = api_key_response
        print(api_key, key_index)
        return {
            **self.DEFAULT_HEADERS,
            "Authorization": f"Bearer {api_key}",
        }

    # ---------------------- Cron endpoints ----------------------
    async def list_jobs(self) -> Tuple[List[Job], bool]:
        """
        List all cron jobs.

        GET /jobs

        Returns:
            Tuple[List[Job], bool]: list of jobs, someFailed flag
        """
        response: JobsListResponse | None = await fetch(
            self.base_url,
            model=JobsListResponse,
            method="GET",
            headers=self._get_headers(),
        )
        if response is None:
            return [], False

        return response.jobs, response.someFailed

    async def get_job(self, job_id: int) -> Optional[DetailedJob]:
        """
        Get a single job by ID.

        GET /jobs/<jobId>

        Args:
            job_id: The job ID to retrieve.

        Returns:
            DetailedJob object or None on error.
        """
        response: DetailedJob | None = await fetch(
            f"{self.base_url}/{job_id}", model=DetailedJob, method="GET"
        )
        if response is None:
            return None
        return response

    async def create_job(self, job_data: DetailedJob) -> Optional[int]:
        """
        Create a new cron job.

        PUT /jobs

        Args:
            job_data: DetailedJob object (only url field is mandatory).

        Returns:
            The created job ID or None on error.
        """
        response: CreateJobResponse | None = await fetch(
            self.base_url,
            model=CreateJobResponse,
            method="POST",
            json=job_data.model_dump(exclude_unset=True),
            headers={
                **self.DEFAULT_HEADERS,
                "Authorization": f"Bearer {self.api_key_manager.get_available_key()}",
            },
        )
        if response is None:
            return None
        return response.jobId

    async def update_job(self, job_id: int, job_data: Dict[str, Any]) -> bool:
        """
        Update an existing job.

        PATCH /jobs/<jobId>

        Args:
            job_id: The job ID to update.
            job_data: Partial job data (only include changed fields).

        Returns:
            True if update succeeded, False otherwise.
        """
        payload = {"job": job_data}
        result = await fetch(
            f"{self.base_url}/{job_id}",
            model=UpdateJobResponse,
            method="PATCH",
            json=payload,
        )
        return result is not None

    async def delete_job(self, job_id: int) -> bool:
        """
        Delete a job.

        DELETE /jobs/<jobId>

        Args:
            job_id: The job ID to delete.

        Returns:
            True if deletion succeeded, False otherwise.
        """
        result = await fetch(
            f"{self.base_url}/{job_id}",
            model=DeleteJobResponse,
            method="DELETE",
        )
        return result is not None
