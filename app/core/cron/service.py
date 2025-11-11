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
    JobSchedule,
    JobsListResponse,
    UpdateJobResponse,
)
from app.core.fetcher import fetch


logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

from typing import List, Optional
from app.core.cron.types import JobSchedule


class JobScheduleBuilder:
    """
    Fluent builder for constructing JobSchedule objects safely.
    Automatically fills wildcard values (-1) for unspecified fields.
    """

    # Allowed ranges for quick validation
    _VALID_RANGES = {
        "hours": (0, 23),
        "minutes": (0, 59),
        "mdays": (1, 31),
        "months": (1, 12),
        "wdays": (0, 6),
    }

    def __init__(
        self,
        timezone: str = "UTC",
        expires_at: int = 0,
        hours: Optional[List[int]] = None,
        minutes: Optional[List[int]] = None,
        mdays: Optional[List[int]] = None,
        months: Optional[List[int]] = None,
        wdays: Optional[List[int]] = None,
    ):
        self.timezone = timezone
        self.expires_at = expires_at
        self.hours = self._sanitize("hours", hours)
        self.minutes = self._sanitize("minutes", minutes)
        self.mdays = self._sanitize("mdays", mdays)
        self.months = self._sanitize("months", months)
        self.wdays = self._sanitize("wdays", wdays)

    # ---------------------------
    # Helpers
    # ---------------------------

    def _sanitize(self, name: str, values: Optional[List[int]]) -> List[int]:
        """Validate and normalize input lists, defaulting to wildcard [-1]."""
        if not values:
            return [-1]
        low, high = self._VALID_RANGES.get(name, (0, 59))
        for v in values:
            if v != -1 and not (low <= v <= high):
                raise ValueError(f"{name} values must be -1 or in {low}-{high}")
        return values

    # ---------------------------
    # Preset schedules
    # ---------------------------

    @classmethod
    def every_minute(cls, timezone: str = "UTC") -> "JobScheduleBuilder":
        """Run every minute."""
        return cls(timezone=timezone, minutes=[-1])

    @classmethod
    def every_hour(cls, timezone: str = "UTC") -> "JobScheduleBuilder":
        """Run every hour at minute 0."""
        return cls(timezone=timezone, minutes=[0])

    @classmethod
    def every_day(
        cls, timezone: str = "UTC", at_hour: int = 0, at_minute: int = 0
    ) -> "JobScheduleBuilder":
        """Run every day at specific time."""
        return cls(timezone=timezone, hours=[at_hour], minutes=[at_minute])

    @classmethod
    def every_week(
        cls,
        timezone: str = "UTC",
        day_of_week: int = 0,
        at_hour: int = 0,
        at_minute: int = 0,
    ) -> "JobScheduleBuilder":
        """Run weekly on a specific day (0=Sunday - 6=Saturday)."""
        return cls(
            timezone=timezone,
            wdays=[day_of_week],
            hours=[at_hour],
            minutes=[at_minute],
        )

    @classmethod
    def every_month(
        cls,
        timezone: str = "UTC",
        day_of_month: int = 1,
        at_hour: int = 0,
        at_minute: int = 0,
    ) -> "JobScheduleBuilder":
        """Run monthly on a specific day."""
        return cls(
            timezone=timezone,
            mdays=[day_of_month],
            hours=[at_hour],
            minutes=[at_minute],
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
        """Run once at a specific date/time (sets expiresAt)."""
        expires_at = int(f"{year:04d}{month:02d}{day:02d}{hour:02d}{minute:02d}00")
        return cls(
            timezone=timezone,
            expires_at=expires_at,
            months=[month],
            mdays=[day],
            hours=[hour],
            minutes=[minute],
            wdays=[-1],
        )

    # ---------------------------
    # Fluent setters
    # ---------------------------

    def set_timezone(self, timezone: str) -> "JobScheduleBuilder":
        self.timezone = timezone
        return self

    def set_expires_at(self, expires_at: int) -> "JobScheduleBuilder":
        self.expires_at = expires_at
        return self

    def set_hours(self, hours: List[int]) -> "JobScheduleBuilder":
        self.hours = self._sanitize("hours", hours)
        return self

    def set_minutes(self, minutes: List[int]) -> "JobScheduleBuilder":
        self.minutes = self._sanitize("minutes", minutes)
        return self

    def set_mdays(self, mdays: List[int]) -> "JobScheduleBuilder":
        self.mdays = self._sanitize("mdays", mdays)
        return self

    def set_months(self, months: List[int]) -> "JobScheduleBuilder":
        self.months = self._sanitize("months", months)
        return self

    def set_wdays(self, wdays: List[int]) -> "JobScheduleBuilder":
        self.wdays = self._sanitize("wdays", wdays)
        return self

    # ---------------------------
    # Build
    # ---------------------------

    def build(self) -> JobSchedule:
        """Return the final JobSchedule model."""
        return JobSchedule(
            timezone=self.timezone,
            expiresAt=self.expires_at,
            hours=self.hours,
            minutes=self.minutes,
            mdays=self.mdays,
            months=self.months,
            wdays=self.wdays,
        )


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
            f"{self.base_url}/{job_id}",
            model=DetailedJob,
            method="GET",
            headers=self._get_headers(),
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
            method="PUT",
            json={"job": job_data.model_dump(exclude_unset=True, mode="json")},
            headers=self._get_headers(),
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
            headers=self._get_headers(),
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
            headers=self._get_headers(),
        )
        return result is not None
