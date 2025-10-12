from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_user_timezone(user_id: str) -> str:
    return "UTC"