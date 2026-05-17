import pytest
from datetime import datetime, timedelta, timezone, date

IST = timezone(timedelta(hours=5, minutes=30))


class TestMarketSessionWeekends:
    def test_saturday_is_closed(self):
        from core.session.market_session import MarketSession
        session = MarketSession()
        saturday = datetime(2026, 5, 16, 12, 0, tzinfo=IST)
        assert session.phase_at(saturday) == "closed"

    def test_sunday_is_closed(self):
        from core.session.market_session import MarketSession
        session = MarketSession()
        sunday = datetime(2026, 5, 17, 12, 0, tzinfo=IST)
        assert session.phase_at(sunday) == "closed"


class TestMarketSessionHolidays:
    def test_republic_day_is_closed(self):
        from core.session.market_session import MarketSession
        session = MarketSession()
        holiday = datetime(2026, 1, 26, 12, 0, tzinfo=IST)
        assert session.phase_at(holiday) == "closed"


class TestMarketSessionPhases:
    @pytest.fixture
    def session(self):
        from core.session.market_session import MarketSession
        return MarketSession()

    def test_pre_market_boundary_0759(self, session):
        dt = datetime(2026, 5, 18, 7, 59, tzinfo=IST)
        assert session.phase_at(dt) == "closed"

    def test_pre_market_boundary_0800(self, session):
        dt = datetime(2026, 5, 18, 8, 0, tzinfo=IST)
        assert session.phase_at(dt) == "pre-market"

    def test_live_boundary_0914(self, session):
        dt = datetime(2026, 5, 18, 9, 14, tzinfo=IST)
        assert session.phase_at(dt) == "pre-market"

    def test_live_boundary_0915(self, session):
        dt = datetime(2026, 5, 18, 9, 15, tzinfo=IST)
        assert session.phase_at(dt) == "live"

    def test_closing_boundary_1514(self, session):
        dt = datetime(2026, 5, 18, 15, 14, tzinfo=IST)
        assert session.phase_at(dt) == "live"

    def test_closing_boundary_1515(self, session):
        dt = datetime(2026, 5, 18, 15, 15, tzinfo=IST)
        assert session.phase_at(dt) == "closing"

    def test_closed_boundary_1529(self, session):
        dt = datetime(2026, 5, 18, 15, 29, tzinfo=IST)
        assert session.phase_at(dt) == "closing"

    def test_closed_boundary_1530(self, session):
        dt = datetime(2026, 5, 18, 15, 30, tzinfo=IST)
        assert session.phase_at(dt) == "closed"

    def test_current_phase_returns_string(self, session):
        phase = session.current_phase()
        assert phase in ("closed", "pre-market", "live", "closing")

    def test_is_market_open_live(self, session):
        dt = datetime(2026, 5, 18, 10, 0, tzinfo=IST)
        assert session.is_market_open(dt) is True

    def test_is_market_open_weekend(self, session):
        dt = datetime(2026, 5, 16, 10, 0, tzinfo=IST)  # Saturday
        assert session.is_market_open(dt) is False
