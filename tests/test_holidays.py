import pytest
from datetime import date
from core.scheduler.holidays import HolidayCalendar


def test_is_weekend():
    cal = HolidayCalendar()
    saturday = date(2026, 5, 16)  # Saturday
    assert cal.is_weekend(saturday) is True
    monday = date(2026, 5, 18)  # Monday
    assert cal.is_weekend(monday) is False


def test_is_holiday():
    cal = HolidayCalendar()
    # Republic Day
    republic_day = date(2026, 1, 26)
    assert cal.is_holiday(republic_day) is True
    # Regular trading day
    normal_day = date(2026, 5, 18)  # Monday
    assert cal.is_holiday(normal_day) is False


def test_is_trading_day():
    cal = HolidayCalendar()
    # Saturday -- no trading
    saturday = date(2026, 5, 16)
    assert cal.is_trading_day(saturday) is False
    # Holiday -- no trading
    republic_day = date(2026, 1, 26)
    assert cal.is_trading_day(republic_day) is False
    # Normal Monday -- trading
    monday = date(2026, 5, 18)
    assert cal.is_trading_day(monday) is True


def test_next_trading_day():
    cal = HolidayCalendar()
    friday = date(2026, 5, 15)  # Friday
    next_day = cal.next_trading_day(friday)
    assert next_day == date(2026, 5, 18)  # Monday (skip weekend)
