from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional


def utc_now() -> datetime:
    """Get current time in UTC with timezone awareness."""
    return datetime.now(timezone.utc)


def get_user_timezone(user_id: str) -> str:
    """Get user timezone. Legacy function for backward compatibility."""
    return "UTC"


def to_user_timezone(dt: datetime, user_timezone: str) -> datetime:
    """
    Convert a UTC datetime to user's local timezone.
    
    Args:
        dt: A timezone-aware datetime in UTC
        user_timezone: IANA timezone name (e.g., 'Asia/Kolkata')
    
    Returns:
        Datetime converted to user's timezone
    """
    if dt.tzinfo is None:
        # If naive, assume it's UTC
        dt = dt.replace(tzinfo=timezone.utc)
    
    user_tz = ZoneInfo(user_timezone)
    return dt.astimezone(user_tz)


def to_utc(dt: datetime, user_timezone: str) -> datetime:
    """
    Convert a datetime from user's local timezone to UTC.
    
    Args:
        dt: A datetime (naive or aware)
        user_timezone: IANA timezone name (e.g., 'Asia/Kolkata')
    
    Returns:
        Timezone-aware datetime in UTC
    """
    if dt.tzinfo is None:
        # If naive, localize it to user's timezone first
        user_tz = ZoneInfo(user_timezone)
        dt = dt.replace(tzinfo=user_tz)
    
    return dt.astimezone(timezone.utc)


def parse_time_in_user_tz(
    time_str: str, user_timezone: str, base_date: Optional[datetime] = None
) -> datetime:
    """
    Parse a time string (HH:MM) in user's timezone and return UTC datetime.
    
    Args:
        time_str: Time in "HH:MM" format (24-hour)
        user_timezone: IANA timezone name
        base_date: Date to apply the time to (defaults to today in user's timezone)
    
    Returns:
        UTC datetime with the specified time in user's timezone
    """
    hours, minutes = map(int, time_str.split(":"))
    
    if base_date is None:
        # Get current date in user's timezone
        user_tz = ZoneInfo(user_timezone)
        base_date = datetime.now(user_tz)
    else:
        # Convert base_date to user's timezone if needed
        base_date = to_user_timezone(base_date, user_timezone)
    
    # Create datetime with specified time in user's timezone
    local_dt = base_date.replace(hour=hours, minute=minutes, second=0, microsecond=0)
    
    # Convert to UTC
    return local_dt.astimezone(timezone.utc)


def format_datetime_for_user(dt: datetime, user_timezone: str, format_str: str = "%b %d, %Y at %I:%M %p") -> str:
    """
    Format a datetime for display to user in their local timezone.
    
    Args:
        dt: UTC datetime
        user_timezone: IANA timezone name
        format_str: strftime format string
    
    Returns:
        Formatted datetime string in user's timezone
    """
    local_dt = to_user_timezone(dt, user_timezone)
    return local_dt.strftime(format_str)


def format_relative_time(dt: datetime, user_timezone: str = "UTC") -> str:
    """
    Format datetime as a human-readable relative time string in user's timezone.
    
    Args:
        dt: UTC datetime to format
        user_timezone: User's IANA timezone name (defaults to UTC for backward compatibility)
    
    Returns:
        Human-readable relative time string
    """
    # Ensure dt is timezone-aware
    if dt.tzinfo is None:
        # If naive, assume it's UTC
        dt = dt.replace(tzinfo=timezone.utc)
    
    now = utc_now()
    diff = dt - now
    
    # Convert to user's timezone for absolute time display
    local_dt = to_user_timezone(dt, user_timezone)
    
    # Past times
    if diff.total_seconds() < 0:
        abs_diff = abs(diff)
        if abs_diff < timedelta(minutes=1):
            return "just now"
        elif abs_diff < timedelta(hours=1):
            mins = int(abs_diff.total_seconds() / 60)
            return f"{mins} minute{'s' if mins != 1 else ''} ago"
        elif abs_diff < timedelta(days=1):
            hours = int(abs_diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif abs_diff < timedelta(days=7):
            days = abs_diff.days
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            return local_dt.strftime("%b %d, %Y at %I:%M %p")
    
    # Future times
    if diff < timedelta(minutes=1):
        return "now"
    elif diff < timedelta(hours=1):
        mins = int(diff.total_seconds() / 60)
        return f"in {mins} minute{'s' if mins != 1 else ''}"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"in {hours} hour{'s' if hours != 1 else ''}"
    elif diff < timedelta(days=7):
        days = diff.days
        return f"in {days} day{'s' if days != 1 else ''}"
    elif diff < timedelta(days=30):
        weeks = diff.days // 7
        return f"in {weeks} week{'s' if weeks != 1 else ''}"
    else:
        return local_dt.strftime("%b %d, %Y at %I:%M %p")