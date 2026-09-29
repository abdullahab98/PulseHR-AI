from datetime import datetime, date
from zoneinfo import ZoneInfo
from app.config import settings

def get_app_timezone() -> ZoneInfo:
    tz_name = getattr(settings, "TIMEZONE", "Asia/Dhaka")
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("Asia/Dhaka")

def get_local_now() -> datetime:
    """
    Returns the current datetime in the configured application timezone (e.g. Asia/Dhaka, UTC+6)
    without tzinfo (naive) for consistent database persistence and date calculations.
    """
    return datetime.now(get_app_timezone()).replace(tzinfo=None)

def get_local_today() -> date:
    """
    Returns today's date in the configured application timezone (Asia/Dhaka).
    """
    return datetime.now(get_app_timezone()).date()
