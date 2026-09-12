from __future__ import annotations

import datetime as dt
import re
from zoneinfo import ZoneInfo

_TIME = r"(?P<hour>\d{1,2}):(?P<minute>\d{2})"

_TODAY_RE = re.compile(rf"^\s*сегодня\s+{_TIME}\s*$", re.IGNORECASE)
_TOMORROW_RE = re.compile(rf"^\s*завтра\s+{_TIME}\s*$", re.IGNORECASE)
_DATE_RE = re.compile(rf"^\s*(?P<day>\d{{1,2}})\.(?P<month>\d{{1,2}})(?:\.(?P<year>\d{{4}}))?\s+{_TIME}\s*$")
_BARE_TIME_RE = re.compile(rf"^\s*{_TIME}\s*$")

HELP_TEXT = (
    "Не понял дату дедлайна. Примеры: «сегодня 21:00», «завтра 09:30», "
    "«15.09 20:00», «15.09.2026 20:00»."
)


class DeadlineParseError(ValueError):
    pass


def _safe_date(year: int, month: int, day: int) -> dt.date:
    try:
        return dt.date(year, month, day)
    except ValueError as exc:
        raise DeadlineParseError(f"Некорректная дата: {day:02d}.{month:02d}.{year}") from exc


def _build_local(base_date: dt.date, hour: int, minute: int, tz: ZoneInfo) -> dt.datetime:
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise DeadlineParseError(f"Некорректное время: {hour:02d}:{minute:02d}")
    return dt.datetime(base_date.year, base_date.month, base_date.day, hour, minute, tzinfo=tz)


def parse_deadline(text: str, timezone_name: str, *, now: dt.datetime | None = None) -> dt.datetime:
    """Parse a Russian-language deadline expression into a UTC-aware datetime.

    Supported formats (case-insensitive):
      - "сегодня 21:00"
      - "завтра 09:30"
      - "15.09 20:00"       (current year; rolled to next year if that moment already passed)
      - "15.09.2026 20:00"
      - "20:00"             (today if still ahead, otherwise tomorrow)
    """
    tz = ZoneInfo(timezone_name)
    now_local = (now or dt.datetime.now(dt.timezone.utc)).astimezone(tz)
    raw = text.strip()

    if m := _TODAY_RE.match(raw):
        local_dt = _build_local(now_local.date(), int(m["hour"]), int(m["minute"]), tz)

    elif m := _TOMORROW_RE.match(raw):
        local_dt = _build_local(now_local.date() + dt.timedelta(days=1), int(m["hour"]), int(m["minute"]), tz)

    elif m := _DATE_RE.match(raw):
        day, month = int(m["day"]), int(m["month"])
        hour, minute = int(m["hour"]), int(m["minute"])
        explicit_year = m["year"] is not None
        year = int(m["year"]) if explicit_year else now_local.year
        local_dt = _build_local(_safe_date(year, month, day), hour, minute, tz)
        if not explicit_year and local_dt <= now_local:
            local_dt = _build_local(_safe_date(year + 1, month, day), hour, minute, tz)

    elif m := _BARE_TIME_RE.match(raw):
        local_dt = _build_local(now_local.date(), int(m["hour"]), int(m["minute"]), tz)
        if local_dt <= now_local:
            local_dt += dt.timedelta(days=1)

    else:
        raise DeadlineParseError(HELP_TEXT)

    return local_dt.astimezone(dt.timezone.utc)
