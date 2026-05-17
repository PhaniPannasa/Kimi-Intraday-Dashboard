from datetime import datetime, time, timedelta, timezone
from core.scheduler.holidays import calendar as holiday_calendar

IST = timezone(timedelta(hours=5, minutes=30))

PRE_MARKET_START = time(8, 0)
LIVE_START = time(9, 15)
CLOSING_START = time(15, 15)
SESSION_END = time(15, 30)


class MarketSession:
    """IST-aware market session phase detector.

    Phases:
      - closed:      weekends, holidays, outside 08:00-15:30
      - pre-market:  08:00-09:15 on trading days
      - live:        09:15-15:15 on trading days
      - closing:     15:15-15:30 on trading days
    """

    def __init__(self):
        self.calendar = holiday_calendar
        self.tz = IST
        self._snapped_at: str | None = None

    def phase_at(self, dt: datetime) -> str:
        """Return market phase for a given datetime."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=self.tz)
        now_ist = dt.astimezone(self.tz)
        today_ist = now_ist.date()

        if not self.calendar.is_trading_day(today_ist):
            return "closed"

        t = now_ist.time()
        if t < PRE_MARKET_START:
            return "closed"
        if t < LIVE_START:
            return "pre-market"
        if t < CLOSING_START:
            return "live"
        if t < SESSION_END:
            return "closing"
        return "closed"

    def current_phase(self) -> str:
        """Return current market phase in IST."""
        return self.phase_at(datetime.now(self.tz))

    def is_market_open(self, dt: datetime | None = None) -> bool:
        """True if market is in live session."""
        if dt is None:
            dt = datetime.now(self.tz)
        return self.phase_at(dt) == "live"

    @property
    def snapped_at(self) -> str | None:
        return self._snapped_at

    @snapped_at.setter
    def snapped_at(self, value: str):
        self._snapped_at = value


session = MarketSession()
