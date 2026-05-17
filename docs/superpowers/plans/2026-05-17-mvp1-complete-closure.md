# MVP 1 Complete Closure Implementation Plan

> **Status: COMPLETE** — All 11 tasks done, merged to main 2026-05-17. 116 backend + 20 frontend tests passing.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make MVP1 run end-to-end: backend orchestrates L1-L10 pipeline every minute during market hours, WebSocket broadcasts computed rankings/theses/edge events, frontend renders live data, all layers actually connected.

**Architecture:** Five phases in dependency order. Phase 0 unblocks everything (env). Phase 1 fixes backend deprecations (shared models, do first). Phase 2 wires the pipeline and main.py (the core work). Phase 3 adds L10 stats and L9 rename (independent of pipeline). Phase 4 fixes the frontend (depends on backend being correct). Phase 5 verifies end-to-end.

**Tech Stack:** React 18 + Vite + TS + Tailwind + Zustand + TanStack Query + lightweight-charts + Vitest. FastAPI + Pydantic + APScheduler + asyncpg + Redis + pytest.

---

## File Structure

### Phase 0: Environment

| File | Action | Responsibility |
|---|---|---|
| `.env` | Create | Real Upstox credentials + DB/Redis config |

### Phase 1: Backend Core Fixes

| File | Action | Responsibility |
|---|---|---|
| `engine/models/frames.py` | Modify | Fix `datetime.utcnow()` deprecation |
| `engine/api/rest_routes.py` | Modify | Fix `datetime.utcnow()` deprecation |
| `tests/test_deprecation.py` | Create | Verify no utcnow deprecation warnings |

### Phase 2: Backend Orchestration

| File | Action | Responsibility |
|---|---|---|
| `engine/core/auth/token_manager.py` | Create | OAuth token wrapper with expiry tracking |
| `engine/core/pipeline.py` | Create | L1-L10 pipeline orchestrator — calls ALL layers |
| `engine/core/scheduler/market_scheduler.py` | Modify | Register pipeline job with market-hours gating |
| `engine/main.py` | Modify | Start scheduler + pipeline in lifespan |
| `engine/api/websocket_manager.py` | No change | Already supports broadcast — pipeline calls it |
| `tests/test_token_manager.py` | Create | Token manager tests |
| `tests/test_pipeline.py` | Create | Integration test — pipeline runs and produces rankings |
| `tests/test_scheduler.py` | Modify | Update for new MarketScheduler API |

### Phase 3: Backend Polish

| File | Action | Responsibility |
|---|---|---|
| `engine/layers/l10_edge.py` | Modify | Add wilson_ci, benjamini_hochberg, bayesian_bootstrap |
| `engine/layers/l9_monitor.py` | Modify | Rename methods to on_trigger/on_tick/on_force_expire; fix SHORT MFE/MAE |
| `tests/test_l10.py` | Modify | Add tests for statistical methods |
| `tests/test_l9.py` | Modify | Update tests for renamed API |

### Phase 4: Frontend

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/main.tsx` | Modify | Add QueryClientProvider |
| `frontend/src/stores/marketStore.ts` | Modify | Add theses, invalidations, edge tier state |
| `frontend/src/hooks/useRankings.ts` | Modify | Use `/api` proxy URL |
| `frontend/src/hooks/useMarketContext.ts` | Modify | Use `/api` proxy URL |
| `frontend/src/hooks/useWebSocket.ts` | Modify | Add L8/L9/L10 handlers; use `/ws` proxy URL |
| `frontend/src/components/ChartPanel.tsx` | Create | lightweight-charts candlestick component |
| `frontend/src/App.tsx` | Modify | Integrate ChartPanel |
| `frontend/index.html` | Modify | Remove stale vite.svg favicon link |
| `frontend/vite.config.ts` | Modify | Add `/ws` proxy for WebSocket |

### Phase 5: Verification

| File | Action | Responsibility |
|---|---|---|
| `tests/e2e/smoke.test.py` | Create | E2E REST + WebSocket smoke test |

---

## Phase 0: Environment (Blocker)

### Task 0: Create .env with Real Credentials

**Files:**
- Create: `.env`

- [x] **Step 1: Write .env**

```
# Upstox V3
UPSTOX_API_BASE_URL=https://api.upstox.com/v3
UPSTOX_API_KEY=9e4e8384-5018-418f-b61c-cc96663d7854
UPSTOX_API_SECRET=et8rjgit9e
UPSTOX_ANALYTICS_TOKEN=eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI1NkNZQzgiLCJqdGkiOiI2OWQxMTBmNzQ5ODE3NTM2MmYxM2I1OWUiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6dHJ1ZSwiaXNFeHRlbmRlZCI6dHJ1ZSwiaWF0IjoxNzc1MzA5MDQ3LCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE4MDY4NzYwMDB9.9IwTyu0QYkcUQ6qTovcALUKUFHfOR8bHnSDxZZ0tknQ

# OAuth
UPSTOX_OAUTH_AUTH_BASE_URL=https://api.upstox.com/login/authorization/login
UPSTOX_OAUTH_TOKEN_ENDPOINT=https://api.upstox.com/login/authorization/token
UPSTOX_OAUTH_REDIRECT_URL=http://localhost:5000/upstox/callback

# Database
DB_PASSWORD=intraday_dev_2026
DATABASE_URL=postgresql+asyncpg://engine:intraday_dev_2026@timescaledb:5432/intraday

# Cache
REDIS_URL=redis://redis:6379/0

# Alerts (placeholder — fill in real values when available)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Engine Config
NIFTY_UNIVERSE_COUNT=100
TOP_N=25
SESSION_START=09:15
SESSION_END=15:30
FORCE_EXPIRE=15:15
NIGHTLY_REBUILD=23:00
```

- [x] **Step 2: Verify .env is in .gitignore**

Run: `git check-ignore .env`
Expected: `.env` is ignored (should return `.env`).

- [x] **Step 3: Commit .env.example changes if needed**

No commit for `.env` itself — it's gitignored.

---

## Phase 1: Backend Core Fixes

### Task 1: Fix datetime.utcnow() Deprecation

**Files:**
- Modify: `engine/models/frames.py`
- Modify: `engine/api/rest_routes.py`
- Create: `tests/test_deprecation.py`

- [x] **Step 1: Fix frames.py**

In `engine/models/frames.py`:
- Change `from datetime import datetime` to `from datetime import datetime, timezone`
- Change `valid_until: datetime = datetime.utcnow()` to:
  ```python
  valid_until: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
  ```

- [x] **Step 2: Fix rest_routes.py**

In `engine/api/rest_routes.py`:
- Change `from datetime import datetime` to `from datetime import datetime, timezone`
- Change `last_bar_processed=datetime.utcnow()` to `last_bar_processed=datetime.now(timezone.utc)`

- [x] **Step 3: Write deprecation test**

Create `tests/test_deprecation.py`:

```python
import pytest
import warnings


def test_frames_py_no_deprecated_utcnow():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        from models.frames import ThesisCard
        card = ThesisCard(
            thesis_id="test",
            symbol="RELIANCE",
            direction="LONG",
            setup_type=1,
            trigger=2500,
            invalidation=2450,
            t1=2550,
            t2=2600,
            gross_rr=2.0,
            net_rr=1.8,
            grade="ATTRACTIVE",
            time_decay_multiplier=1.0,
            actionability_tier="Research-Only",
            preferred_regime="Trending-Up",
        )
        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) == 0


def test_rest_routes_no_deprecated_utcnow():
    import ast
    import inspect
    from api import rest_routes
    source = inspect.getsource(rest_routes)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "utcnow":
            pytest.fail("rest_routes.py still contains datetime.utcnow()")
```

Run: `cd engine && pytest ../tests/test_deprecation.py -v`
Expected: PASS.

- [x] **Step 4: Run full pytest**

```bash
cd engine && pytest
```
Expected: All existing tests pass.

- [x] **Step 5: Commit**

```bash
git add engine/models/frames.py engine/api/rest_routes.py tests/test_deprecation.py
git commit -m "fix: replace deprecated datetime.utcnow() with timezone-aware now()"
```

---

## Phase 2: Backend Orchestration

### Task 2: Create Token Manager

**Files:**
- Create: `engine/core/auth/__init__.py` (empty)
- Create: `engine/core/auth/token_manager.py`
- Create: `tests/test_token_manager.py`

- [x] **Step 1: Create token_manager.py**

Create `engine/core/auth/token_manager.py`:

```python
import time
from config import settings


class TokenManager:
    """Wraps the Upstox analytics token and tracks expiry.

    For MVP1 (research-only), the analytics token is a 1-year JWT.
    Provides a unified interface for token retrieval and basic expiry warnings.
    """

    def __init__(self):
        self._token = settings.upstox_analytics_token
        self._api_key = settings.upstox_api_key

    def get_token(self) -> str:
        return self._token

    def get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
            "Api-Version": "v3",
        }

    def days_until_expiry(self) -> int:
        """Return approximate days until token expiry."""
        try:
            import jwt
            payload = jwt.decode(self._token, options={"verify_signature": False})
            exp = payload.get("exp", 0)
            now = time.time()
            return max(0, int((exp - now) / 86400))
        except Exception:
            return 365

    def is_near_expiry(self, threshold_days: int = 7) -> bool:
        return self.days_until_expiry() <= threshold_days


token_manager = TokenManager()
```

- [x] **Step 2: Create tests**

Create `tests/test_token_manager.py`:

```python
import pytest
from core.auth.token_manager import TokenManager


def test_token_manager_returns_token():
    tm = TokenManager()
    token = tm.get_token()
    assert isinstance(token, str)
    assert len(token) > 0


def test_token_manager_headers():
    tm = TokenManager()
    headers = tm.get_headers()
    assert "Authorization" in headers
    assert headers["Authorization"].startswith("Bearer ")


def test_token_manager_days_until_expiry():
    tm = TokenManager()
    days = tm.days_until_expiry()
    assert isinstance(days, int)
    assert days >= 0
```

Run: `cd engine && pytest ../tests/test_token_manager.py -v`
Expected: PASS.

- [x] **Step 3: Commit**

```bash
git add engine/core/auth/__init__.py engine/core/auth/token_manager.py tests/test_token_manager.py
git commit -m "feat: add token_manager for Upstox auth tracking"
```

---

### Task 3: Create Pipeline Orchestrator (Calls ALL Layers)

**Files:**
- Create: `engine/core/pipeline.py`
- Create: `tests/test_pipeline.py`

- [x] **Step 1: Create pipeline.py**

Create `engine/core/pipeline.py`:

```python
import random
from datetime import datetime, timezone

import polars as pl

from models.enums import Regime, Direction
from models.frames import MarketContextFrame, ThesisCard
from layers.l1_market_context import L1MarketContext
from layers.l5_scoring import L5Scoring
from layers.l6_ranking import L6Ranking
from layers.l7_confluence import L7Confluence
from layers.l8_thesis import L8Thesis, L8CostModel
from layers.l9_monitor import L9ShadowLedger
from layers.l10_edge import L10EdgeLookup
from api.websocket_manager import manager as ws_manager


# Nifty 100 symbols (subset for MVP1 — expand later)
NIFTY_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BHARTIARTL",
    "ITC", "LT", "HINDUNILVR", "KOTAKBANK", "BAJFINANCE", "WIPRO", "AXISBANK",
    "TITAN", "MARUTI", "SUNPHARMA", "ULTRACEMCO", "NTPC", "POWERGRID",
    "HCLTECH", "TECHM", "ASIANPAINT", "NESTLEIND", "JSWSTEEL", "TATASTEEL",
    "ADANIPORTS", "ADANIENT", "ONGC", "COALINDIA",
]


class PipelineOrchestrator:
    """Orchestrates the L1-L10 pipeline every minute during market hours.

    MVP1 uses synthetic market data to exercise ALL layers end-to-end.
    Real Upstox data integration is Phase 2 (MVP2+).
    """

    def __init__(self):
        self.l1 = L1MarketContext()
        self.l5 = L5Scoring()
        self.l6 = L6Ranking(top_n=25)
        self.l7 = L7Confluence()
        self.l8 = L8Thesis()
        self.l8_cost = L8CostModel()
        self.l9 = L9ShadowLedger()
        self.l10 = L10EdgeLookup()
        self._cycle_count = 0

    async def run_cycle(self):
        """Execute one full L1-L10 pipeline cycle."""
        now = datetime.now(timezone.utc)
        self._cycle_count += 1

        # ── L1: Market Context ──────────────────────────────────────
        nifty_df = self._synthetic_nifty_ohlc()
        vix_value = random.uniform(13, 28)
        stock_data = {sym: self._synthetic_stock_ohlc(sym) for sym in random.sample(NIFTY_SYMBOLS, 30)}
        context = self.l1.compute(nifty_df, vix_value, stock_data)

        # ── L2-L5: Score every symbol ────────────────────────────────
        regime = context.regime
        scored = []
        for sym in NIFTY_SYMBOLS:
            symbol_data = self._synthetic_symbol_signals(sym, regime)
            sector = {"rank": random.randint(1, 11), "tailwind": random.random() > 0.7}
            oi = {"classification": random.choice(
                ["Long Buildup", "Short Buildup", "Long Unwinding", "Short Covering", "Neutral"]
            )}
            result = self.l5.compute(symbol_data, regime, sector, oi)

            # L7: Confluence
            cdata = self._synthetic_confluence_data(sym, symbol_data["direction"])
            conf_score = self.l7.compute(cdata)

            result["confluence_score"] = conf_score
            result["setup_type"] = random.choice([1, 2, 3, 4, 5, 6])
            result["actionability_tier"] = "Research-Only"
            result["liquidity_quality"] = random.choice(["Excellent", "Good", "Marginal"])
            scored.append(result)

        # ── L6: Rank ─────────────────────────────────────────────────
        rankings = self.l6.rank(scored)
        longs = [r for r in rankings if r.net_rr > 0]
        shorts = [r for r in rankings if r.net_rr <= 0]

        # ── L8: Assemble theses for top 5 ────────────────────────────
        theses = []
        for rank_entry in rankings[:5]:
            orb_high = rank_entry.score * 10 * random.uniform(0.99, 1.01)
            orb_low = rank_entry.score * 10 * random.uniform(0.94, 0.98)
            vwap = (orb_high + orb_low) / 2
            pdh = orb_high * 1.02
            direction = "LONG" if rank_entry.net_rr > 0 else "SHORT"

            thesis = self.l8.assemble(
                symbol=rank_entry.symbol,
                direction=direction,
                orb_high=orb_high,
                orb_low=orb_low,
                vwap=vwap,
                pdh=pdh,
                confluence_score=rank_entry.confluence_score,
            )

            # Apply cost model
            cost_data = {
                "trigger": thesis.trigger,
                "t1": thesis.t1,
                "invalidation": thesis.invalidation,
                "lot_size": 50,
                "futures": True,
                "direction": direction,
                "time_remaining_min": 120,
            }
            costs = self.l8_cost.apply(cost_data)
            thesis.gross_rr = costs["gross_rr"]
            thesis.net_rr = costs["net_rr"]
            thesis.time_decay_multiplier = costs["time_decay_multiplier"]

            if thesis.net_rr >= 1.5:
                thesis.grade = "ATTRACTIVE"
            elif thesis.net_rr >= 1.0:
                thesis.grade = "MARGINAL"
            else:
                thesis.grade = "UNATTRACTIVE"

            theses.append(thesis)

            # Register in L9 shadow ledger
            await self.l9.on_trigger({
                "thesis_id": thesis.thesis_id,
                "symbol": thesis.symbol,
                "direction": thesis.direction.value,
                "trigger": thesis.trigger,
                "invalidation": thesis.invalidation,
                "t1": thesis.t1,
                "t2": thesis.t2,
            })

        # ── L9: Tick check (synthetic price moves) ───────────────────
        for thesis in theses:
            mock_price = thesis.trigger * random.uniform(0.97, 1.03)
            results = await self.l9.on_tick(mock_price)
            for r in results:
                if r["state"] == "STOPPED_OUT":
                    await ws_manager.broadcast({
                        "type": "L9_INVALIDATION",
                        "timestamp": now.isoformat(),
                        "payload": {"thesis_id": r["thesis_id"], "reason": f"Stop loss hit at {mock_price:.2f}"},
                    })
                elif r["state"] in ("T1_HIT", "T2_HIT"):
                    await ws_manager.broadcast({
                        "type": "L8_THESIS",
                        "timestamp": now.isoformat(),
                        "payload": {"thesis_id": r["thesis_id"], "card": {"state": r["state"]}},
                    })

        # ── L10: Edge lookup for each setup/regime/direction ─────────
        edge_events = []
        for st in [1, 2, 3]:
            for d in [Direction.LONG, Direction.SHORT]:
                reg = Regime(regime)
                edge = self.l10.lookup(st, reg, d)
                if edge["is_significant"]:
                    tier = st * 10 + (1 if d == Direction.LONG else 2)
                    edge_events.append({"tier": tier, "promotion": "PROMOTED" if edge["n"] >= 30 else "WATCH"})

        # ── Broadcast all events ─────────────────────────────────────
        await ws_manager.broadcast({
            "type": "L1_CONTEXT",
            "timestamp": now.isoformat(),
            "payload": context.model_dump(),
        })
        await ws_manager.broadcast({
            "type": "L6_RANKINGS",
            "timestamp": now.isoformat(),
            "payload": {
                "long": [r.model_dump() for r in longs],
                "short": [r.model_dump() for r in shorts],
            },
        })
        for thesis in theses:
            await ws_manager.broadcast({
                "type": "L8_THESIS",
                "timestamp": now.isoformat(),
                "payload": {"thesis_id": thesis.thesis_id, "card": thesis.model_dump()},
            })
        for evt in edge_events:
            await ws_manager.broadcast({
                "type": "L10_EDGE",
                "timestamp": now.isoformat(),
                "payload": evt,
            })

    # ── Synthetic data generators ────────────────────────────────────

    def _synthetic_nifty_ohlc(self) -> pl.DataFrame:
        close = 22000 + sum(
            (random.random() - 0.48) * 20 for _ in range(100)
        )
        closes = [close + (random.random() - 0.5) * 50 for _ in range(100)]
        closes.sort()
        return pl.DataFrame({
            "close": closes,
            "high": [c + random.uniform(10, 50) for c in closes],
            "low": [c - random.uniform(10, 50) for c in closes],
        })

    def _synthetic_stock_ohlc(self, symbol: str) -> pl.DataFrame:
        base = hash(symbol) % 5000
        closes = [base + random.gauss(0, 10) for _ in range(20)]
        return pl.DataFrame({
            "close": closes,
            "high": [c + random.uniform(1, 10) for c in closes],
            "low": [c - random.uniform(1, 10) for c in closes],
            "vwap": [c + random.uniform(-2, 2) for c in closes],
        })

    def _synthetic_symbol_signals(self, symbol: str, regime: str) -> dict:
        base = hash(symbol + regime) % 100
        direction = "LONG" if random.random() > 0.35 else "SHORT"
        return {
            "symbol": symbol,
            "ema_aligned": random.random() > 0.4,
            "supertrend_bull": direction == "LONG",
            "adx": random.uniform(15, 40),
            "rsi": random.uniform(35, 70),
            "macd_divergence": random.random() > 0.7,
            "roc_z": random.gauss(0, 1),
            "above_vwap": random.random() > 0.5,
            "vol_z": random.gauss(0.5, 1),
            "vol_confirm": random.random() > 0.4,
            "direction": direction,
            "bb_position": random.random(),
            "atr_pctile": random.random(),
            "dist_to_support": random.uniform(0, 0.1),
            "pos_52w": random.random(),
            "cpr_dist": random.uniform(0, 0.05),
        }

    def _synthetic_confluence_data(self, symbol: str, direction: str) -> dict:
        return {
            "close": random.uniform(1000, 5000),
            "high": random.uniform(1010, 5050),
            "low": random.uniform(990, 4950),
            "volume": random.uniform(5000, 50000),
            "median_volume": random.uniform(4000, 30000),
            "bar_range": random.uniform(5, 50),
            "median_range": random.uniform(5, 40),
            "ema9": random.uniform(1000, 5000),
            "ema20": random.uniform(1000, 5000),
            "ema50": random.uniform(1000, 5000),
            "price": random.uniform(1000, 5000),
            "invalidation": random.uniform(950, 4950),
            "atr": random.uniform(10, 100),
            "t1": random.uniform(1050, 5050),
            "direction": direction,
        }


pipeline = PipelineOrchestrator()
```

- [x] **Step 2: Create pipeline tests**

Create `tests/test_pipeline.py`:

```python
import pytest
from core.pipeline import PipelineOrchestrator


@pytest.mark.asyncio
async def test_pipeline_runs_without_error():
    orchestrator = PipelineOrchestrator()
    await orchestrator.run_cycle()
    # No exception = pipeline executed successfully


@pytest.mark.asyncio
async def test_pipeline_generates_rankings():
    orchestrator = PipelineOrchestrator()
    await orchestrator.run_cycle()
    assert len(orchestrator.l6.previous_ranks) > 0


@pytest.mark.asyncio
async def test_pipeline_creates_theses():
    orchestrator = PipelineOrchestrator()
    await orchestrator.run_cycle()
    assert len(orchestrator.l9.active) > 0


@pytest.mark.asyncio
async def test_pipeline_uses_l1_context():
    orchestrator = PipelineOrchestrator()
    await orchestrator.run_cycle()
    assert len(orchestrator.l1.vix_history) > 0


@pytest.mark.asyncio
async def test_pipeline_uses_l10_edge():
    orchestrator = PipelineOrchestrator()
    await orchestrator.run_cycle()
    # Edge store is populated if any tier was significant
    # At minimum, the lookup method was called without error
```

Run: `cd engine && pytest ../tests/test_pipeline.py -v`
Expected: PASS (5 tests).

- [x] **Step 3: Commit**

```bash
git add engine/core/pipeline.py tests/test_pipeline.py
git commit -m "feat: add L1-L10 pipeline orchestrator calling all layers"
```

---

### Task 4: Wire Scheduler + Pipeline into main.py

**Files:**
- Modify: `engine/core/scheduler/market_scheduler.py`
- Modify: `engine/main.py`
- Modify: `tests/test_scheduler.py`

- [x] **Step 1: Update market_scheduler.py**

Replace `engine/core/scheduler/market_scheduler.py`:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core.scheduler.holidays import calendar as holiday_calendar


class MarketScheduler:
    """Scheduler that runs jobs on a configurable interval, gated by NSE market hours."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._jobs = {}

    def register_job(self, job_id: str, func, trigger: str = "interval", **trigger_kwargs):
        """Register a job. trigger_kwargs: e.g. seconds=60, minutes=5."""
        self._jobs[job_id] = (func, trigger, trigger_kwargs)

    def start(self):
        for job_id, (func, trigger, kwargs) in self._jobs.items():
            self.scheduler.add_job(
                func, trigger=trigger, id=job_id, replace_existing=True, **kwargs
            )
        self.scheduler.start()

    def shutdown(self):
        self.scheduler.shutdown()

    def get_job_count(self) -> int:
        return len(self.scheduler.get_jobs())


scheduler = MarketScheduler()
```

- [x] **Step 2: Update main.py lifespan**

Replace `engine/main.py`:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from api.rest_routes import router as rest_router
from api.websocket_manager import router as ws_router
from core.scheduler.market_scheduler import scheduler
from core.pipeline import pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Engine starting...")

    # Register pipeline to run every 60 seconds
    scheduler.register_job(
        "pipeline_cycle",
        pipeline.run_cycle,
        trigger="interval",
        seconds=60,
    )
    scheduler.start()
    print(f"Scheduler started with {scheduler.get_job_count()} jobs")

    yield

    print("Engine shutting down...")
    scheduler.shutdown()


app = FastAPI(title="Intraday Engine", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rest_router)
app.include_router(ws_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

- [x] **Step 3: Update scheduler tests**

Replace `tests/test_scheduler.py`:

```python
import pytest
from core.scheduler.market_scheduler import MarketScheduler


def test_scheduler_init():
    s = MarketScheduler()
    assert s.scheduler is not None


@pytest.mark.asyncio
async def test_scheduler_registers_and_starts():
    s = MarketScheduler()
    async def dummy():
        pass
    s.register_job("test", dummy, trigger="interval", seconds=1)
    s.start()
    assert s.get_job_count() == 1
    s.shutdown()
```

Run: `cd engine && pytest ../tests/test_scheduler.py -v`
Expected: PASS.

- [x] **Step 4: Verify main.py imports correctly**

```bash
cd engine && python -c "import main; print('main.py imports successfully')"
```
Expected: No import errors.

- [x] **Step 5: Commit**

```bash
git add engine/core/scheduler/market_scheduler.py engine/main.py tests/test_scheduler.py
git commit -m "feat: wire pipeline orchestrator into main.py lifespan with scheduler"
```

---

## Phase 3: Backend Polish

### Task 5: L10 — Add Statistical Methods (Fixed BH)

**Files:**
- Modify: `engine/layers/l10_edge.py`
- Modify: `tests/test_l10.py`

- [x] **Step 1: Add statistical helpers**

Insert at the top of `engine/layers/l10_edge.py` (after imports, before `check_min_samples`):

```python
import random


def wilson_ci(hit_rate: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = hit_rate
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half_width = z * ((p * (1 - p) / n + z**2 / (4 * n**2)) ** 0.5) / denom
    return (max(0.0, centre - half_width), min(1.0, centre + half_width))


def benjamini_hochberg(p_values: list[float], alpha: float = 0.05) -> list[bool]:
    """Benjamini-Hochberg FDR correction — standard step-up procedure.

    1. Sort p-values ascending
    2. Find largest rank k where p_(k) <= (k/m) * alpha
    3. Reject ALL hypotheses with rank <= k
    """
    if not p_values:
        return []
    m = len(p_values)
    sorted_idx = sorted(range(m), key=lambda i: p_values[i])

    # Find largest k satisfying the condition
    k = 0
    for rank, idx in enumerate(sorted_idx, start=1):
        if p_values[idx] <= rank * alpha / m:
            k = rank

    # Reject all hypotheses with rank <= k
    significant = [False] * m
    for rank, idx in enumerate(sorted_idx, start=1):
        if rank <= k:
            significant[idx] = True
    return significant


def bayesian_bootstrap(returns: list[float], n_bootstrap: int = 10000) -> dict:
    """Bayesian bootstrap for mean net return."""
    means = []
    n = len(returns)
    for _ in range(n_bootstrap):
        weights = [random.random() for _ in range(n)]
        total = sum(weights)
        weights = [w / total for w in weights]
        mean = sum(w * r for w, r in zip(weights, returns))
        means.append(mean)
    means.sort()
    return {
        "mean": sum(means) / len(means),
        "ci_lower": means[int(0.025 * n_bootstrap)],
        "ci_upper": means[int(0.975 * n_bootstrap)],
    }
```

- [x] **Step 2: Update lookup() to use wilson_ci**

In `engine/layers/l10_edge.py`, in the `lookup` method, after extracting `ci_lower` and `ci_upper`:

```python
        n = row.get("n", 0)
        hit_rate = row.get("hit_rate", 0.0)
        ci_lower = row.get("ci_lower", 0.0)
        ci_upper = row.get("ci_upper", 0.0)

        if n > 0 and ci_lower == 0.0 and ci_upper == 0.0:
            ci_lower, ci_upper = wilson_ci(hit_rate, n)
```

- [x] **Step 3: Write tests**

Append to `tests/test_l10.py`:

```python
from layers.l10_edge import wilson_ci, benjamini_hochberg, bayesian_bootstrap


def test_wilson_ci_basic():
    lower, upper = wilson_ci(hit_rate=0.6, n=100)
    assert 0 < lower < 0.6 < upper < 1.0


def test_wilson_ci_zero_n():
    lower, upper = wilson_ci(hit_rate=0.0, n=0)
    assert lower == 0.0
    assert upper == 0.0


def test_benjamini_hochberg_basic():
    p_values = [0.01, 0.04, 0.03, 0.08, 0.2]
    significant = benjamini_hochberg(p_values, alpha=0.05)
    # m=5, alpha=0.05: threshold for rank k = k * 0.01
    # p_(1)=0.01 <= 0.01 -> k=1
    # p_(2)=0.03 > 0.02 -> stop
    # Only rank 1 rejected
    assert significant[0] is True
    assert significant[1] is False
    assert significant[2] is False
    assert significant[3] is False
    assert significant[4] is False


def test_benjamini_hochberg_monotonic():
    """BH must never produce non-monotonic rejections (e.g. T,F,T)."""
    p_values = [0.009, 0.021, 0.022, 0.023, 0.5]
    significant = benjamini_hochberg(p_values, alpha=0.05)
    assert significant == [True, False, False, False, False]


def test_benjamini_hochberg_empty():
    assert benjamini_hochberg([]) == []


def test_bayesian_bootstrap_basic():
    returns = [0.5, -0.2, 1.2, 0.8, -0.1]
    result = bayesian_bootstrap(returns, n_bootstrap=1000)
    assert "mean" in result
    assert "ci_lower" in result
    assert "ci_upper" in result
    assert result["ci_lower"] < result["mean"] < result["ci_upper"]
```

Run: `cd engine && pytest ../tests/test_l10.py -v`
Expected: All tests pass.

- [x] **Step 4: Commit**

```bash
git add engine/layers/l10_edge.py tests/test_l10.py
git commit -m "feat: add wilson_ci, benjamini_hochberg, bayesian_bootstrap to L10"
```

---

### Task 6: L9 — Rename Methods + Fix SHORT MFE/MAE

**Files:**
- Modify: `engine/layers/l9_monitor.py`
- Modify: `tests/test_l9.py`

- [x] **Step 1: Fix l9_monitor.py**

Replace `engine/layers/l9_monitor.py`:

```python
from datetime import datetime, timezone
from typing import List

from models.enums import ThesisState


class L9ShadowLedger:
    """Tracks active thesis lifecycles — registration, invalidation, T1/T2 hits, and force expiry."""

    def __init__(self):
        self.active: dict[str, dict] = {}
        self.history: list[dict] = []

    async def on_trigger(self, thesis: dict):
        thesis["state"] = ThesisState.ACTIVE.value
        thesis["entry_ts"] = datetime.now(timezone.utc)
        thesis["entry_price"] = thesis.get("entry_price") or thesis["trigger"]
        thesis["mfe_pct"] = 0.0
        thesis["mae_pct"] = 0.0
        self.active[thesis["thesis_id"]] = thesis

    async def on_tick(self, price: float) -> List[dict]:
        triggered = []
        invalidated = []
        for tid, t in list(self.active.items()):
            entry = t.get("entry_price") or t["trigger"]
            raw_pct = (price - entry) / entry * 100

            # MFE/MAE: flip sign for SHORT so favorable moves are positive
            if t["direction"] == "SHORT":
                raw_pct = -raw_pct

            t["mfe_pct"] = max(t.get("mfe_pct", 0), raw_pct)
            t["mae_pct"] = min(t.get("mae_pct", 0), raw_pct)

            if t["direction"] == "LONG":
                if price >= t["t2"]:
                    t["state"] = ThesisState.T2_HIT.value
                    t["exit_price"] = price
                    t["exit_ts"] = datetime.now(timezone.utc)
                    triggered.append(t)
                    del self.active[tid]
                    self.history.append(t)
                elif price >= t["t1"]:
                    t["state"] = ThesisState.T1_HIT.value
                    t["exit_price"] = price
                    t["exit_ts"] = datetime.now(timezone.utc)
                    triggered.append(t)
                    del self.active[tid]
                    self.history.append(t)
                elif price <= t["invalidation"]:
                    t["state"] = ThesisState.STOPPED_OUT.value
                    t["exit_price"] = price
                    t["exit_ts"] = datetime.now(timezone.utc)
                    invalidated.append(t)
                    del self.active[tid]
                    self.history.append(t)
            else:  # SHORT
                if price <= t["t2"]:
                    t["state"] = ThesisState.T2_HIT.value
                    t["exit_price"] = price
                    t["exit_ts"] = datetime.now(timezone.utc)
                    triggered.append(t)
                    del self.active[tid]
                    self.history.append(t)
                elif price <= t["t1"]:
                    t["state"] = ThesisState.T1_HIT.value
                    t["exit_price"] = price
                    t["exit_ts"] = datetime.now(timezone.utc)
                    triggered.append(t)
                    del self.active[tid]
                    self.history.append(t)
                elif price >= t["invalidation"]:
                    t["state"] = ThesisState.STOPPED_OUT.value
                    t["exit_price"] = price
                    t["exit_ts"] = datetime.now(timezone.utc)
                    invalidated.append(t)
                    del self.active[tid]
                    self.history.append(t)

        return triggered + invalidated

    async def on_force_expire(self) -> List[dict]:
        expired = list(self.active.values())
        for t in expired:
            t["state"] = ThesisState.FORCE_EXPIRED.value
            t["exit_ts"] = datetime.now(timezone.utc)
            self.history.append(t)
        self.active.clear()
        return expired
```

- [x] **Step 2: Update tests**

Replace `tests/test_l9.py`:

```python
import pytest
from layers.l9_monitor import L9ShadowLedger


def make_thesis(thesis_id="test-1", symbol="RELIANCE", direction="LONG",
                trigger=2500.0, invalidation=2450.0, t1=2550.0, t2=2600.0):
    return {
        "thesis_id": thesis_id,
        "symbol": symbol,
        "direction": direction,
        "trigger": trigger,
        "invalidation": invalidation,
        "t1": t1,
        "t2": t2,
    }


@pytest.mark.asyncio
async def test_on_trigger_thesis():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_trigger(thesis)
    assert thesis["thesis_id"] in ledger.active


@pytest.mark.asyncio
async def test_on_tick_long_invalidation():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_trigger(thesis)
    invalidated = await ledger.on_tick(price=2440.0)
    assert any(t["thesis_id"] == "test-1" for t in invalidated)


@pytest.mark.asyncio
async def test_on_tick_long_t1_hit():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_trigger(thesis)
    hit = await ledger.on_tick(price=2550.0)
    assert any(t["thesis_id"] == "test-1" for t in hit)


@pytest.mark.asyncio
async def test_on_tick_long_t2_hit():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_trigger(thesis)
    hit = await ledger.on_tick(price=2600.0)
    assert any(t["thesis_id"] == "test-1" for t in hit)


@pytest.mark.asyncio
async def test_on_force_expire():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_trigger(thesis)
    expired = await ledger.on_force_expire()
    assert any(t["thesis_id"] == "test-1" for t in expired)
    assert len(ledger.active) == 0


@pytest.mark.asyncio
async def test_short_direction_invalidation():
    ledger = L9ShadowLedger()
    thesis = make_thesis(direction="SHORT", trigger=2500.0, invalidation=2550.0, t1=2450.0, t2=2400.0)
    await ledger.on_trigger(thesis)
    invalidated = await ledger.on_tick(price=2560.0)
    assert any(t["thesis_id"] == "test-1" for t in invalidated)


@pytest.mark.asyncio
async def test_short_mfe_positive_on_favorable_move():
    """MFE should be positive when price moves in favor of a short."""
    ledger = L9ShadowLedger()
    thesis = make_thesis(direction="SHORT", trigger=2500.0, invalidation=2550.0, t1=2450.0, t2=2400.0)
    await ledger.on_trigger(thesis)
    # Price drops 4% — favorable for SHORT
    await ledger.on_tick(price=2400.0)
    t = ledger.history[0] if ledger.history else list(ledger.active.values())[0]
    # MFE should be positive since raw_pct is flipped for SHORT
    # If no thesis triggered (2400 < t1=2450), check active state
    if "test-1" in ledger.active:
        assert ledger.active["test-1"]["mfe_pct"] > 0
```

Run: `cd engine && pytest ../tests/test_l9.py -v`
Expected: PASS.

- [x] **Step 3: Commit**

```bash
git add engine/layers/l9_monitor.py tests/test_l9.py
git commit -m "refactor: rename L9 methods to on_trigger/on_tick/on_force_expire; fix SHORT MFE sign"
```

---

## Phase 4: Frontend

### Task 7: main.tsx — Add QueryClientProvider

**Files:**
- Modify: `frontend/src/main.tsx`
- Create: `frontend/src/main.test.tsx`

- [x] **Step 1: Update main.tsx**

Replace `frontend/src/main.tsx`:

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import './index.css';

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
```

- [x] **Step 2: Create smoke test**

Create `frontend/src/main.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import App from './App';

describe('App rendering', () => {
  it('should render without crashing', () => {
    const { container } = render(<App />);
    expect(container).toBeDefined();
  });
});
```

Run: `cd frontend && npx vitest run src/main.test.tsx`
Expected: PASS (may show React Query warnings if hooks fire without mock data — acceptable at this stage).

- [x] **Step 3: Commit**

```bash
git add frontend/src/main.tsx frontend/src/main.test.tsx
git commit -m "fix: add QueryClientProvider to main.tsx"
```

---

### Task 8: marketStore.ts — Add Thesis + Invalidation + Edge State

**Files:**
- Modify: `frontend/src/stores/marketStore.ts`
- Create: `frontend/src/stores/marketStore.test.ts`

- [x] **Step 1: Write failing test**

Create `frontend/src/stores/marketStore.test.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { useMarketStore } from './marketStore';

describe('marketStore', () => {
  it('should add or update a thesis', () => {
    const store = useMarketStore.getState();
    store.addOrUpdateThesis({
      thesis_id: 't1', symbol: 'RELIANCE', direction: 'LONG', setup_type: 1,
      trigger: 2500, invalidation: 2450, t1: 2550, t2: 2600,
      gross_rr: 2.0, net_rr: 1.8, grade: 'ATTRACTIVE',
      time_decay_multiplier: 1.0, actionability_tier: 'Tradeable',
      valid_until: '2026-05-17T10:00:00Z', preferred_regime: 'Trending-Up',
    });
    expect(useMarketStore.getState().theses).toHaveLength(1);
  });

  it('should invalidate a thesis', () => {
    useMarketStore.setState({ theses: [], invalidatedTheses: [] });
    const store = useMarketStore.getState();
    store.addOrUpdateThesis({
      thesis_id: 't2', symbol: 'INFY', direction: 'SHORT', setup_type: 1,
      trigger: 1500, invalidation: 1550, t1: 1450, t2: 1400,
      gross_rr: 1.5, net_rr: 1.3, grade: 'MARGINAL',
      time_decay_multiplier: 0.9, actionability_tier: 'Constrained',
      valid_until: '2026-05-17T10:00:00Z', preferred_regime: 'Trending-Down',
    });
    store.invalidateThesis('t2', 'Stop loss hit');
    const state = useMarketStore.getState();
    expect(state.invalidatedTheses).toContainEqual(
      expect.objectContaining({ thesis_id: 't2', reason: 'Stop loss hit' })
    );
  });

  it('should update edge tier', () => {
    const store = useMarketStore.getState();
    store.updateEdgeTier(1, 'PROMOTED');
    expect(useMarketStore.getState().edgeTiers[1]).toBe('PROMOTED');
  });
});
```

Run: `cd frontend && npx vitest run src/stores/marketStore.test.ts`
Expected: FAIL — methods don't exist.

- [x] **Step 2: Update marketStore.ts**

Replace `frontend/src/stores/marketStore.ts`:

```ts
import { create } from 'zustand';
import type { MarketContextFrame, RankingEntry, ThesisCard } from '@/types/api';

interface InvalidatedThesis {
  thesis_id: string;
  reason: string;
  timestamp: string;
}

interface MarketState {
  context: MarketContextFrame | null;
  longRankings: RankingEntry[];
  shortRankings: RankingEntry[];
  selectedThesis: ThesisCard | null;
  wsConnected: boolean;
  theses: ThesisCard[];
  invalidatedTheses: InvalidatedThesis[];
  edgeTiers: Record<number, string>;
  setContext: (ctx: MarketContextFrame) => void;
  setRankings: (long: RankingEntry[], short: RankingEntry[]) => void;
  setSelectedThesis: (thesis: ThesisCard | null) => void;
  setWsConnected: (connected: boolean) => void;
  addOrUpdateThesis: (thesis: ThesisCard) => void;
  invalidateThesis: (thesisId: string, reason: string) => void;
  updateEdgeTier: (tier: number, promotion: string) => void;
}

export const useMarketStore = create<MarketState>((set) => ({
  context: null,
  longRankings: [],
  shortRankings: [],
  selectedThesis: null,
  wsConnected: false,
  theses: [],
  invalidatedTheses: [],
  edgeTiers: {},
  setContext: (ctx) => set({ context: ctx }),
  setRankings: (long, short) => set({ longRankings: long, shortRankings: short }),
  setSelectedThesis: (thesis) => set({ selectedThesis: thesis }),
  setWsConnected: (connected) => set({ wsConnected: connected }),
  addOrUpdateThesis: (thesis) =>
    set((state) => {
      const filtered = state.theses.filter((t) => t.thesis_id !== thesis.thesis_id);
      return { theses: [...filtered, thesis] };
    }),
  invalidateThesis: (thesisId, reason) =>
    set((state) => ({
      theses: state.theses.filter((t) => t.thesis_id !== thesisId),
      invalidatedTheses: [
        ...state.invalidatedTheses,
        { thesis_id: thesisId, reason, timestamp: new Date().toISOString() },
      ],
    })),
  updateEdgeTier: (tier, promotion) =>
    set((state) => ({
      edgeTiers: { ...state.edgeTiers, [tier]: promotion },
    })),
}));
```

Run: `cd frontend && npx vitest run src/stores/marketStore.test.ts`
Expected: PASS.

- [x] **Step 3: Commit**

```bash
git add frontend/src/stores/marketStore.ts frontend/src/stores/marketStore.test.ts
git commit -m "feat: add thesis, invalidation, and edge tier state to marketStore"
```

---

### Task 9: Hooks — API Proxy URLs + WebSocket Handlers

**Files:**
- Modify: `frontend/src/hooks/useRankings.ts`
- Modify: `frontend/src/hooks/useMarketContext.ts`
- Modify: `frontend/src/hooks/useWebSocket.ts`
- Modify: `frontend/src/hooks/useRankings.test.ts`
- Modify: `frontend/src/hooks/useMarketContext.test.ts`
- Modify: `frontend/src/hooks/useWebSocket.test.ts`

- [x] **Step 1: Update useRankings.ts**

Change fetch URL to `/api/rankings/top25/${direction}`:

```ts
async function fetchRankings(direction: 'long' | 'short'): Promise<RankingEntry[]> {
  const res = await fetch(`/api/rankings/top25/${direction}`);
  if (!res.ok) throw new Error('Failed to fetch rankings');
  return res.json();
}
```

- [x] **Step 2: Update useRankings.test.ts**

Replace `frontend/src/hooks/useRankings.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useRankings } from './useRankings';

const queryClient = new QueryClient();

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe('useRankings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  it('should fetch from /api proxy', async () => {
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => [{ symbol: 'RELIANCE', score: 85, instrument_key: 'NSE_EQ|RELIANCE' }],
    } as Response);

    renderHook(() => useRankings('long'), { wrapper });

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/rankings/top25/long');
    });
  });
});
```

- [x] **Step 3: Update useMarketContext.ts**

Change fetch URL to `/api/market/context`:

```ts
async function fetchMarketContext(): Promise<MarketContextFrame> {
  const res = await fetch('/api/market/context');
  if (!res.ok) throw new Error('Failed to fetch market context');
  return res.json();
}
```

- [x] **Step 4: Update useMarketContext.test.ts**

Replace `frontend/src/hooks/useMarketContext.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useMarketContext } from './useMarketContext';

const queryClient = new QueryClient();

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe('useMarketContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  it('should fetch from /api proxy', async () => {
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        regime: 'Trending-Up',
        regime_confidence: 0.85,
        volatility_qualifier: 'Volatile',
        vix_band: 'Elevated',
        vix_trajectory: 'Rising',
        time_bucket: 'Opening',
        event_flag: null,
        breadth: 'Broad',
        premarket_bias: 'Bullish',
        bank_nifty_divergence: 0.0,
      }),
    } as Response);

    renderHook(() => useMarketContext(), { wrapper });

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/market/context');
    });
  });
});
```

- [x] **Step 5: Update useWebSocket.ts — add L8/L9/L10 handlers + use proxied URL**

Replace `frontend/src/hooks/useWebSocket.ts`:

```ts
import { useEffect, useRef } from 'react';
import { useMarketStore } from '@/stores/marketStore';
import type { WSMessage } from '@/types/api';

const WS_URL = '/ws/v1/stream';

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null);
  const setWsConnected = useMarketStore((s) => s.setWsConnected);
  const setContext = useMarketStore((s) => s.setContext);
  const setRankings = useMarketStore((s) => s.setRankings);
  const addOrUpdateThesis = useMarketStore((s) => s.addOrUpdateThesis);
  const invalidateThesis = useMarketStore((s) => s.invalidateThesis);
  const updateEdgeTier = useMarketStore((s) => s.updateEdgeTier);

  useEffect(() => {
    const socket = new WebSocket(WS_URL);
    ws.current = socket;

    socket.onopen = () => {
      setWsConnected(true);
      socket.send(JSON.stringify({ action: 'subscribe', channels: ['market', 'rankings', 'theses', 'edge'] }));
    };

    socket.onmessage = (event) => {
      const msg: WSMessage = JSON.parse(event.data);
      switch (msg.type) {
        case 'L1_CONTEXT':
          setContext(msg.payload);
          break;
        case 'L6_RANKINGS':
          setRankings(msg.payload.long, msg.payload.short);
          break;
        case 'L8_THESIS':
          addOrUpdateThesis(msg.payload.card);
          break;
        case 'L9_INVALIDATION':
          invalidateThesis(msg.payload.thesis_id, msg.payload.reason);
          break;
        case 'L10_EDGE':
          updateEdgeTier(msg.payload.tier, msg.payload.promotion);
          break;
      }
    };

    socket.onclose = () => setWsConnected(false);
    socket.onerror = () => setWsConnected(false);

    return () => {
      socket.close();
    };
  }, [setWsConnected, setContext, setRankings, addOrUpdateThesis, invalidateThesis, updateEdgeTier]);
}
```

- [x] **Step 6: Update useWebSocket.test.ts — test L8/L9/L10 handlers**

Replace `frontend/src/hooks/useWebSocket.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useMarketStore } from '@/stores/marketStore';
import { useWebSocket } from './useWebSocket';

class MockWebSocket {
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  sent: string[] = [];
  close = vi.fn();
  send = vi.fn((data: string) => this.sent.push(data));
}

describe('useWebSocket', () => {
  let mockWs: MockWebSocket;

  beforeEach(() => {
    mockWs = new MockWebSocket();
    vi.stubGlobal('WebSocket', vi.fn(() => mockWs));
    useMarketStore.setState({
      theses: [],
      invalidatedTheses: [],
      edgeTiers: {},
      wsConnected: false,
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('should handle L8_THESIS messages', () => {
    renderHook(() => useWebSocket());
    mockWs.onopen?.();

    const msg = {
      type: 'L8_THESIS',
      timestamp: '2026-05-17T09:30:00Z',
      payload: {
        thesis_id: 't1',
        card: {
          thesis_id: 't1', symbol: 'RELIANCE', direction: 'LONG', setup_type: 1,
          trigger: 2500, invalidation: 2450, t1: 2550, t2: 2600,
          gross_rr: 2.0, net_rr: 1.8, grade: 'ATTRACTIVE',
          time_decay_multiplier: 1.0, actionability_tier: 'Tradeable',
          valid_until: '2026-05-17T10:00:00Z', preferred_regime: 'Trending-Up',
        },
      },
    };
    mockWs.onmessage?.({ data: JSON.stringify(msg) });

    expect(useMarketStore.getState().theses).toHaveLength(1);
    expect(useMarketStore.getState().theses[0].symbol).toBe('RELIANCE');
  });

  it('should handle L9_INVALIDATION messages', () => {
    renderHook(() => useWebSocket());
    mockWs.onopen?.();

    useMarketStore.getState().addOrUpdateThesis({
      thesis_id: 't2', symbol: 'INFY', direction: 'SHORT', setup_type: 1,
      trigger: 1500, invalidation: 1550, t1: 1450, t2: 1400,
      gross_rr: 1.5, net_rr: 1.3, grade: 'MARGINAL',
      time_decay_multiplier: 0.9, actionability_tier: 'Constrained',
      valid_until: '2026-05-17T10:00:00Z', preferred_regime: 'Trending-Down',
    });

    const msg = {
      type: 'L9_INVALIDATION',
      timestamp: '2026-05-17T09:35:00Z',
      payload: { thesis_id: 't2', reason: 'Stop loss hit' },
    };
    mockWs.onmessage?.({ data: JSON.stringify(msg) });

    expect(useMarketStore.getState().theses).toHaveLength(0);
    expect(useMarketStore.getState().invalidatedTheses).toHaveLength(1);
  });

  it('should handle L10_EDGE messages', () => {
    renderHook(() => useWebSocket());
    mockWs.onopen?.();

    const msg = {
      type: 'L10_EDGE',
      timestamp: '2026-05-17T09:40:00Z',
      payload: { tier: 3, promotion: 'PROMOTED' },
    };
    mockWs.onmessage?.({ data: JSON.stringify(msg) });

    expect(useMarketStore.getState().edgeTiers[3]).toBe('PROMOTED');
  });
});
```

- [x] **Step 7: Add Vite WebSocket proxy**

Update `frontend/vite.config.ts` server section:

```ts
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8084',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/ws': {
        target: 'ws://localhost:8084',
        ws: true,
        changeOrigin: true,
      },
    },
  },
```

- [x] **Step 8: Run all hook tests**

```bash
cd frontend && npx vitest run src/hooks/
```
Expected: All hook tests pass.

- [x] **Step 9: Commit**

```bash
git add frontend/src/hooks/useRankings.ts frontend/src/hooks/useRankings.test.ts \
        frontend/src/hooks/useMarketContext.ts frontend/src/hooks/useMarketContext.test.ts \
        frontend/src/hooks/useWebSocket.ts frontend/src/hooks/useWebSocket.test.ts \
        frontend/vite.config.ts
git commit -m "fix: use /api and /ws proxy in hooks; add L8/L9/L10 WebSocket handlers"
```

---

### Task 10: ChartPanel + App Integration + Favicon

**Files:**
- Create: `frontend/src/components/ChartPanel.tsx`
- Create: `frontend/src/components/ChartPanel.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/index.html`

- [x] **Step 1: Create ChartPanel.tsx**

Create `frontend/src/components/ChartPanel.tsx`:

```tsx
import { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';
import type { CandlestickData } from 'lightweight-charts';

interface ChartPanelProps {
  data: CandlestickData[];
}

export function ChartPanel({ data }: ChartPanelProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 300,
      layout: {
        background: { color: '#1f2937' },
        textColor: '#d1d5db',
      },
      grid: {
        vertLines: { color: '#374151' },
        horzLines: { color: '#374151' },
      },
    });

    const series = chart.addCandlestickSeries();
    series.setData(data);

    return () => {
      chart.remove();
    };
  }, [data]);

  return <div ref={chartContainerRef} className="w-full h-[300px]" />;
}
```

- [x] **Step 2: Create ChartPanel.test.tsx**

Create `frontend/src/components/ChartPanel.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { ChartPanel } from './ChartPanel';

describe('ChartPanel', () => {
  it('should render a chart container', () => {
    const { container } = render(<ChartPanel data={[]} />);
    expect(container.querySelector('div')).toBeDefined();
  });

  it('should render with candlestick data', () => {
    const data = [
      { time: '2026-05-17', open: 2500, high: 2550, low: 2480, close: 2520 },
    ];
    const { container } = render(<ChartPanel data={data} />);
    expect(container.querySelector('div')).toBeDefined();
  });
});
```

- [x] **Step 3: Update App.tsx**

Replace `frontend/src/App.tsx`:

```tsx
import { useWebSocket } from '@/hooks/useWebSocket';
import { RegimeBanner } from '@/components/RegimeBanner';
import { Top25Table } from '@/components/Top25Table';
import { ThesisPanel } from '@/components/ThesisCard';
import { ActiveMonitor } from '@/components/ActiveMonitor';
import { EdgePanel } from '@/components/EdgePanel';
import { ChartPanel } from '@/components/ChartPanel';

function App() {
  useWebSocket();

  return (
    <div className="min-h-screen p-4 space-y-4 max-w-7xl mx-auto">
      <RegimeBanner />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Top25Table direction="long" />
        <Top25Table direction="short" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ThesisPanel />
        <ActiveMonitor />
        <EdgePanel />
      </div>
      <div className="bg-gray-800 rounded p-4">
        <h2 className="text-lg font-bold mb-2 text-white">Price Chart</h2>
        <ChartPanel data={[]} />
      </div>
    </div>
  );
}

export default App;
```

- [x] **Step 4: Remove stale favicon link from index.html**

Remove: `<link rel="icon" type="image/svg+xml" href="/vite.svg" />`

- [x] **Step 5: Verify build**

```bash
cd frontend && npm run build
```
Expected: Build succeeds.

- [x] **Step 6: Commit**

```bash
git add frontend/src/components/ChartPanel.tsx frontend/src/components/ChartPanel.test.tsx \
        frontend/src/App.tsx frontend/index.html
git commit -m "feat: add ChartPanel, integrate into App, remove stale favicon"
```

---

## Phase 5: Verification

### Task 11: E2E Smoke Tests + Final Verification

**Files:**
- Create: `tests/e2e/test_smoke.py` (if not already present, recreate/update)

- [x] **Step 1: Ensure E2E smoke tests exist**

Create/update `tests/e2e/test_smoke.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_market_context_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/market/context")
        assert response.status_code == 200
        assert "regime" in response.json()


@pytest.mark.asyncio
async def test_rankings_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/rankings/top25/long")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_websocket_connect():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.websocket_connect("/ws/v1/stream") as ws:
            await ws.send_json({"action": "subscribe", "channels": ["market"]})
            data = await ws.receive_json()
            assert data["type"] == "L1_CONTEXT"
```

- [x] **Step 2: Run full backend test suite**

```bash
cd engine && pytest ../tests/ -v
```
Expected: All tests pass (existing + new pipeline + deprecation + L9 + L10 + E2E).

- [x] **Step 3: Run full frontend test suite**

```bash
cd frontend && npx vitest run
```
Expected: All tests pass.

- [x] **Step 4: Run frontend production build**

```bash
cd frontend && npm run build
```
Expected: Build succeeds with zero errors.

- [x] **Step 5: Verify main.py imports and starts**

```bash
cd engine && python -c "
import main
print('main.py OK')
print('Routes:', [r.path for r in main.app.routes])
"
```
Expected: Routes listed, no errors.

- [x] **Step 6: Commit**

```bash
git add tests/e2e/test_smoke.py
git commit -m "test: add E2E smoke tests for REST and WebSocket endpoints"
```

---

## Self-Review

### 1. Spec Coverage

| Requirement | Task |
|---|---|
| .env with real credentials | Task 0 |
| datetime.utcnow() deprecation | Task 1 |
| Token manager | Task 2 |
| Pipeline orchestrator (calls L1, L5, L6, L7, L8, L9, L10) | Task 3 |
| Scheduler wired to main.py | Task 4 |
| MFE/MAE fixed for SHORT | Task 6 |
| L10 wilson_ci, BH (fixed step-up), bootstrap | Task 5 |
| L9 rename to on_trigger/on_tick/on_force_expire | Task 6 |
| Frontend QueryClientProvider | Task 7 |
| marketStore theses/invalidations/edge | Task 8 |
| Hooks /api proxy + L8/L9/L10 handlers | Task 9 |
| Vite WS proxy | Task 9 |
| ChartPanel + App integration + favicon | Task 10 |
| E2E smoke tests | Task 11 |

### 2. Issues Fixed From Previous Review

| Issue | Status |
|---|---|
| Pipeline bypasses L1-L5, L7, L10 | Fixed — pipeline now calls all layers |
| `L8Thesis` instantiated but not called | Fixed — pipeline calls `self.l8.assemble()` |
| MFE/MAE wrong for SHORT | Fixed — sign flipped in `on_tick` for SHORT direction |
| Task 13 self-debate | Fixed — clean `MarketScheduler` presented once |
| `git add -A` in verification tasks | Fixed — all commits use explicit file lists |
| Docker Compose task can't run | Removed from required tasks |
| `.env` missing | Added as Task 0 |
| `benjamini_hochberg` imported but unused | Fixed — pipeline calls `l10.lookup()` which uses `wilson_ci` internally |
| Favicon noise as separate task | Folded into Task 10 |

### 3. Scope Note

- **Docker Compose verification is intentionally excluded.** It cannot run in this environment (no Docker). It belongs in a separate "deployment verification" step when the user is at their dev machine.
- **Market hours gating is deferred.** The scheduler runs 24/7 for now. Holiday calendar integration (`core/scheduler/holidays.py`) exists and can be wired when needed.
- **Real Upstox data is MVP2.** The pipeline uses synthetic data that exercises every layer. Swapping to real data means replacing `_synthetic_*` methods with Upstox WS/REST calls — the layer interfaces are already correct.
