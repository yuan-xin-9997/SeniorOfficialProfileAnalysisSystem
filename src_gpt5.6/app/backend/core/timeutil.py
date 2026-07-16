"""Time helpers.

All timestamps are stored as timezone-aware UTC in the database. Anything shown
to the user is converted to Beijing time (Asia/Shanghai), per CLAUDE.md 规范2.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

UTC = timezone.utc
# 中国标准时间自 1991 年起无夏令时；固定 UTC+8 可避免 Windows 缺少
# IANA tzdata 时导致整个服务无法启动。
BEIJING = timezone(timedelta(hours=8), name="Asia/Shanghai")


def utcnow() -> datetime:
    """Current time as timezone-aware UTC."""
    return datetime.now(UTC)


def to_beijing(dt: datetime) -> datetime:
    """Convert a datetime to Beijing time. Naive datetimes assumed UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(BEIJING)


def format_beijing(dt: datetime | None) -> str | None:
    """``YYYY-MM-DD HH:MM:SS`` in Beijing time, or None."""
    if dt is None:
        return None
    return to_beijing(dt).strftime("%Y-%m-%d %H:%M:%S")


def iso_beijing(dt: datetime | None) -> str | None:
    """ISO 8601 string in Beijing time, or None."""
    if dt is None:
        return None
    return to_beijing(dt).isoformat()
