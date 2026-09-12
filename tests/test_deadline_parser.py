import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from bot.services.deadline_parser import DeadlineParseError, parse_deadline

TZ = "Europe/Moscow"
NOW = dt.datetime(2026, 9, 12, 10, 0, tzinfo=ZoneInfo(TZ)).astimezone(dt.timezone.utc)


def test_parses_today():
    result = parse_deadline("сегодня 21:00", TZ, now=NOW)
    local = result.astimezone(ZoneInfo(TZ))
    assert (local.year, local.month, local.day, local.hour, local.minute) == (2026, 9, 12, 21, 0)


def test_parses_tomorrow_case_insensitive():
    result = parse_deadline("ЗАВТРА 09:30", TZ, now=NOW)
    local = result.astimezone(ZoneInfo(TZ))
    assert (local.month, local.day, local.hour, local.minute) == (9, 13, 9, 30)


def test_parses_explicit_date_current_year():
    result = parse_deadline("20.09 20:00", TZ, now=NOW)
    local = result.astimezone(ZoneInfo(TZ))
    assert (local.year, local.month, local.day, local.hour, local.minute) == (2026, 9, 20, 20, 0)


def test_rolls_over_to_next_year_if_date_already_passed():
    result = parse_deadline("01.01 10:00", TZ, now=NOW)
    local = result.astimezone(ZoneInfo(TZ))
    assert local.year == 2027


def test_parses_explicit_year():
    result = parse_deadline("15.09.2027 08:00", TZ, now=NOW)
    local = result.astimezone(ZoneInfo(TZ))
    assert (local.year, local.month, local.day) == (2027, 9, 15)


def test_bare_time_rolls_to_tomorrow_if_passed():
    result = parse_deadline("09:00", TZ, now=NOW)  # NOW is 10:00 local
    local = result.astimezone(ZoneInfo(TZ))
    assert (local.day, local.hour) == (13, 9)


def test_bare_time_stays_today_if_still_ahead():
    result = parse_deadline("23:00", TZ, now=NOW)
    local = result.astimezone(ZoneInfo(TZ))
    assert (local.day, local.hour) == (12, 23)


def test_invalid_format_raises():
    with pytest.raises(DeadlineParseError):
        parse_deadline("когда-нибудь потом", TZ, now=NOW)


def test_invalid_time_raises():
    with pytest.raises(DeadlineParseError):
        parse_deadline("сегодня 25:00", TZ, now=NOW)


def test_invalid_date_raises():
    with pytest.raises(DeadlineParseError):
        parse_deadline("31.02 10:00", TZ, now=NOW)
