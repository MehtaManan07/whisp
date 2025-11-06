from datetime import datetime, timedelta, time
from typing import Optional, Tuple, List
from dateutil.relativedelta import relativedelta
from pydantic import ValidationError
from zoneinfo import ZoneInfo

from app.modules.reminders.types import RecurrenceConfig, RecurrenceType


class RemindersUtils:
    @staticmethod
    def _parse_target_time(
        recurrence_config: Optional[RecurrenceConfig],
    ) -> Optional[Tuple[int, int]]:
        """Parse target time from recurrence config (HH:MM)."""
        if recurrence_config and recurrence_config.time:
            try:
                parsed_time = datetime.strptime(recurrence_config.time, "%H:%M").time()
                return parsed_time.hour, parsed_time.minute
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
    def _advance_time(
        dt: datetime,
        days: int = 0,
        weeks: int = 0,
        months: int = 0,
        years: int = 0,
        target_time: Optional[Tuple[int, int]] = None,
    ) -> datetime:
        """Advance datetime by given period and apply target time."""
        dt += relativedelta(days=days, weeks=weeks, months=months, years=years)
        return RemindersUtils._apply_target_time(dt, target_time)

    @staticmethod
    def _calculate_daily_trigger(
        base_time: datetime, target_time: Optional[Tuple[int, int]]
    ) -> datetime:
        today_target = RemindersUtils._apply_target_time(base_time, target_time)
        if base_time < today_target:
            return today_target
        return RemindersUtils._advance_time(base_time, days=1, target_time=target_time)

    @staticmethod
    def _calculate_weekly_trigger(
        base_time: datetime,
        recurrence_config: RecurrenceConfig,
        target_time: Optional[Tuple[int, int]],
    ) -> datetime:
        if not recurrence_config.days:
            raise ValidationError("Weekly recurrence requires 'days' in config")

        current_day = base_time.weekday()  # 0 = Monday
        days_ahead = min((d - current_day) % 7 for d in recurrence_config.days)
        return RemindersUtils._advance_time(
            base_time, days=days_ahead, target_time=target_time
        )

    @staticmethod
    def _calculate_monthly_trigger(
        base_time: datetime,
        recurrence_config: RecurrenceConfig,
        target_time: Optional[Tuple[int, int]],
    ) -> datetime:
        if not recurrence_config.day:
            raise ValidationError("Monthly recurrence requires 'day' in config")
        # Advance one month, day automatically handles month-end
        return base_time + relativedelta(
            months=+1,
            day=recurrence_config.day,
            hour=(target_time[0] if target_time else 0),
            minute=(target_time[1] if target_time else 0),
            second=0,
            microsecond=0,
        )

    @staticmethod
    def _calculate_yearly_trigger(
        base_time: datetime,
        recurrence_config: RecurrenceConfig,
        target_time: Optional[Tuple[int, int]],
    ) -> datetime:
        if not recurrence_config.month or not recurrence_config.day:
            raise ValidationError(
                "Yearly recurrence requires 'month' and 'day' in config"
            )
        return base_time + relativedelta(
            years=+1,
            month=recurrence_config.month,
            day=recurrence_config.day,
            hour=(target_time[0] if target_time else 0),
            minute=(target_time[1] if target_time else 0),
            second=0,
            microsecond=0,
        )

    @staticmethod
    def calculate_next_trigger(
        base_time: datetime,
        recurrence_type: RecurrenceType,
        recurrence_config: Optional[RecurrenceConfig],
        user_timezone: str = "UTC",
    ) -> datetime:
        """Calculate next trigger datetime in UTC based on recurrence."""
        tz = ZoneInfo(user_timezone)
        base_time_local = base_time.astimezone(tz)

        target_time = RemindersUtils._parse_target_time(recurrence_config)

        if recurrence_type == RecurrenceType.ONCE:
            next_trigger_local = base_time_local
        elif recurrence_type == RecurrenceType.DAILY:
            next_trigger_local = RemindersUtils._calculate_daily_trigger(
                base_time_local, target_time
            )
        elif recurrence_type == RecurrenceType.WEEKLY:
            if recurrence_config is None:
                raise ValidationError("Weekly recurrence requires config")
            next_trigger_local = RemindersUtils._calculate_weekly_trigger(
                base_time_local, recurrence_config, target_time
            )
        elif recurrence_type == RecurrenceType.MONTHLY:
            if recurrence_config is None:
                raise ValidationError("Monthly recurrence requires config")
            next_trigger_local = RemindersUtils._calculate_monthly_trigger(
                base_time_local, recurrence_config, target_time
            )
        elif recurrence_type == RecurrenceType.YEARLY:
            if recurrence_config is None:
                raise ValidationError("Yearly recurrence requires config")
            next_trigger_local = RemindersUtils._calculate_yearly_trigger(
                base_time_local, recurrence_config, target_time
            )
        else:
            raise ValidationError(f"Unsupported recurrence type: {recurrence_type}")

        # Return UTC datetime
        return next_trigger_local.astimezone(ZoneInfo("UTC"))
