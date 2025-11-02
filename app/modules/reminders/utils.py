from datetime import datetime, timedelta
from typing import Optional, Tuple
from dateutil.relativedelta import relativedelta

from pydantic import ValidationError

from app.modules.reminders.types import RecurrenceConfig


class RemindersUtils:
    @staticmethod
    def _parse_target_time(
        recurrence_config: Optional[RecurrenceConfig],
    ) -> Optional[Tuple[int, int]]:
        """Parse target time from recurrence config."""
        if recurrence_config and recurrence_config.time:
            try:
                hours, minutes = map(int, recurrence_config.time.split(":"))
                if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                    raise ValidationError(
                        f"Invalid time format: {recurrence_config.time}"
                    )
                return (hours, minutes)
            except ValueError:
                raise ValidationError(f"Invalid time format: {recurrence_config.time}")
        return None

    @staticmethod
    def _apply_target_time(
        dt: datetime, target_time: Optional[Tuple[int, int]]
    ) -> datetime:
        """Apply target time to a datetime object."""
        if target_time:
            return dt.replace(
                hour=target_time[0], minute=target_time[1], second=0, microsecond=0
            )
        return dt

    @staticmethod
    def _calculate_daily_trigger(
        base_time: datetime, target_time: Optional[Tuple[int, int]]
    ) -> datetime:
        """Calculate next trigger for daily recurrence."""
        if target_time:
            # Check if target time for today has already passed
            today_target = RemindersUtils._apply_target_time(base_time, target_time)

            if base_time < today_target:
                # Target time hasn't passed today, schedule for today
                return today_target
            else:
                # Target time has passed today, schedule for tomorrow
                tomorrow = base_time + timedelta(days=1)
                return RemindersUtils._apply_target_time(tomorrow, target_time)
        else:
            # No specific time, just add a day
            return base_time + timedelta(days=1)

    @staticmethod
    def _calculate_weekly_trigger(
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
        return RemindersUtils._apply_target_time(next_trigger, target_time)

    @staticmethod
    def _calculate_monthly_trigger(
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

        return RemindersUtils._apply_target_time(next_trigger, target_time)

    @staticmethod
    def _calculate_yearly_trigger(
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

        return RemindersUtils._apply_target_time(next_trigger, target_time)
