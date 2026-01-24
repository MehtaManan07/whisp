import logging
from typing import Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    APScheduler-based background task scheduler.
    Manages interval-based jobs for reminders and email processing.
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._started = False

    def start(self) -> None:
        """Start the scheduler."""
        if not self._started:
            self.scheduler.start()
            self._started = True
            logger.info("Scheduler started")

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the scheduler."""
        if self._started:
            self.scheduler.shutdown(wait=wait)
            self._started = False
            logger.info("Scheduler stopped")

    def add_interval_job(
        self,
        func: Callable,
        minutes: int,
        job_id: str,
        run_immediately: bool = False,
        **kwargs,
    ) -> None:
        """
        Add an interval-based job to the scheduler.
        
        Args:
            func: The async function to run
            minutes: Interval in minutes
            job_id: Unique identifier for the job
            run_immediately: If True, run the job immediately on startup
            **kwargs: Additional arguments passed to add_job
        """
        trigger = IntervalTrigger(minutes=minutes)
        
        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            **kwargs,
        )
        
        logger.info(f"Added job '{job_id}' with interval {minutes} minutes")
        
        # Optionally run immediately
        if run_immediately:
            # Get the job and run it
            job = self.scheduler.get_job(job_id)
            if job:
                self.scheduler.modify_job(job_id, next_run_time=None)
                # Re-add to trigger immediately
                self.scheduler.reschedule_job(job_id, trigger=trigger)

    def remove_job(self, job_id: str) -> bool:
        """
        Remove a job from the scheduler.
        
        Args:
            job_id: The job ID to remove
            
        Returns:
            True if job was removed, False if not found
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job '{job_id}'")
            return True
        except Exception:
            logger.warning(f"Job '{job_id}' not found")
            return False

    def get_jobs(self) -> list:
        """Get all scheduled jobs."""
        return self.scheduler.get_jobs()

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._started
