from datetime import datetime, timezone, timedelta


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_user_timezone(user_id: str) -> str:
    return "UTC"


def format_relative_time(dt: datetime) -> str:
    """Format datetime as a human-readable relative time string."""
    now = utc_now()
    diff = dt - now
    
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
            return dt.strftime("%b %d, %Y at %H:%M")
    
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
        return dt.strftime("%b %d, %Y at %H:%M")