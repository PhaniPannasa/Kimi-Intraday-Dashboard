from datetime import date
from typing import Set

NSE_HOLIDAYS_2026: Set[date] = {
    date(2026, 1, 26),   # Republic Day
    date(2026, 3, 14),   # Holi
    date(2026, 3, 20),   # Id-ul-Fitr (tentative)
    date(2026, 4, 14),   # Dr. Ambedkar Jayanti
    date(2026, 4, 18),   # Good Friday
    date(2026, 5, 1),    # Maharashtra Day
    date(2026, 8, 15),   # Independence Day
    date(2026, 10, 2),   # Gandhi Jayanti
    date(2026, 10, 20),  # Dussehra
    date(2026, 11, 9),   # Diwali (Laxmi Pujan)
    date(2026, 12, 25),  # Christmas
}


class HolidayCalendar:
    def __init__(self, holidays: Set[date] = None):
        self.holidays = holidays or NSE_HOLIDAYS_2026

    def is_weekend(self, d: date) -> bool:
        return d.weekday() >= 5  # Saturday=5, Sunday=6

    def is_holiday(self, d: date) -> bool:
        return d in self.holidays

    def is_trading_day(self, d: date) -> bool:
        return not self.is_weekend(d) and not self.is_holiday(d)

    def next_trading_day(self, d: date) -> date:
        next_day = d + date.resolution
        while not self.is_trading_day(next_day):
            next_day += date.resolution
        return next_day


calendar = HolidayCalendar()
