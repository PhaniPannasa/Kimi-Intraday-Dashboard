# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Where the code actually lives

**All application code lives at the repository ROOT** (not in a worktree).

```
.
├── engine/                    # FastAPI backend (Python 3.11)
│   ├── main.py                # ASGI entrypoint with lifespan management
│   ├── config.py              # pydantic-settings
│   ├── pyproject.toml         # deps + setuptools config
│   ├── api/                   # rest_routes.py (REST endpoints), websocket_manager.py
│   ├── core/                  # pipeline orchestration
│   │   ├── pipeline.py        # TickBuffer, BarAggregator, PipelineOrchestrator (L1-L10)
│   │   ├── data/              # upstox_rest.py, upstox_ws.py, nse_scraper.py, redis_cache.py
│   │   ├── scheduler/         # market_scheduler.py, holidays.py
│   │   ├── session/           # market_session.py (09:15-15:30 IST awareness)
│   │   ├── alerts/            # telegram.py
│   │   └── auth/              # token_manager.py
│   ├── layers/                # l1_market_context … l10_edge (one file per L-layer)
│   ├── models/                # enums.py, frames.py, factors.py (Pydantic v2)
│   └── db/                    # timescale.py + migrations/*.sql
├── frontend/                  # React 18 + Vite + TS PWA
│   ├── src/
│   │   ├── components/        # RegimeBanner, Top25Table, ThesisCard, ActiveMonitor, EdgePanel, etc.
│   │   ├── hooks/             # useWebSocket, useRankings, useMarketContext, etc.
│   │   ├── stores/            # marketStore.ts (Zustand)
│   │   ├── types/             # API contract types
│   │   └── App.tsx
│   ├── vite.config.ts         # Vite build config with /api proxy
│   └── package.json           # dependencies
├── tests/                     # pytest integration + unit + e2e tests
│   ├── test_l1.py … test_l10.py
│   ├── test_pipeline.py       # L1-L10 orchestration test
│   ├── test_pipeline_status.py
│   ├── test_factors_api.py
│   └── e2e/                   # smoke tests
├── docker-compose.yml         # 4-service stack (engine, timescaledb, redis, caddy)
├── .env.example               # template for env vars
└── pytest.ini, pyproject.toml # test + build config
```

## Common commands

Run commands from the **project ROOT** (not a subdirectory).

### Backend (FastAPI engine)

```powershell
# Install deps (editable, with test extras)
pip install -e "./engine[.test]"

# Run dev server (auto-reload on :8000 inside, :8172 outside Docker)
cd engine && uvicorn main:app --host 0.0.0.0 --port 8172 --reload

# All tests (pytest.ini at root auto-discovers tests/)
pytest

# Single test file or test
pytest tests/test_l5.py
pytest tests/test_l5.py::test_score_clamping
pytest tests/test_pipeline.py

# E2E smoke (hits the live ASGI app via httpx)
pytest tests/e2e/
```

**Note:** `pytest.ini` sets `asyncio_mode = auto` — do NOT add `@pytest.mark.asyncio`;
`async def test_*` is picked up automatically. `tests/conftest.py` inserts
`engine/` into `sys.path` so `from main import app` works without packaging.

### Frontend (React PWA)

```powershell
cd frontend
npm install
npm run dev        # Vite on :8190, proxies /api → http://localhost:8172
npm run build      # tsc + vite build → dist/
npm test           # vitest (jsdom, setup in src/test-setup.ts)
```

### Full stack via Docker Compose

```powershell
# Ensure .env exists at project root with Upstox credentials
cp .env.example .env
# Edit .env with real UPSTOX_ANALYTICS_TOKEN, DB_PASSWORD, etc.

# Start all services
docker compose up -d

# Watch engine logs
docker compose logs -f engine

# Stop services
docker compose down
```

**Note:** `.env` is required for Upstox API access; see `.env.example` for template.

## Port mapping (non-obvious — host ports differ from container ports)

Host ports are shifted because the dev machine already runs other services on
the canonical ports. Use these when hitting the stack from the host:

| Service        | Container | Host  | Why                                  |
|----------------|-----------|-------|--------------------------------------|
| TimescaleDB    | 5432      | 8150  | dedicated 8150-8200 block for app    |
| Redis          | 6379      | 8160  | dedicated 8150-8200 block for app    |
| FastAPI engine | 8000      | 8172  | dedicated 8150-8200 block for app    |
| Caddy / web    | 80        | 8180  | dedicated 8150-8200 block for app    |
| Vite dev       | —         | 8190  | proxies `/api` → :8172, `/ws` → :8172 |

**Reserved set for THIS app:** the entire **8150–8200** block. Live
assignments: `8150` (DB), `8160` (Redis), `8172` (engine + WebSocket),
`8170` (unused — former engine port), `8180` (Caddy/web), `8190` (Vite dev);
the rest of the block is held for
future services in this app.
**Do NOT touch** ports owned by other projects on this dev machine — notably
`5173` (Python-Demo-Trading), `5175` (legacy port — left untouched),
`5180` (Stock-Strategy-App), `5432, 6379, 15432` (other databases on this machine),
`5000, 8765` (OpenAlgo), `8000, 8001, 8083` (other python/java services).

**Cloudflare Tunnel:** this app shares the `intraday-edge` tunnel
(UUID `f0a9d271-…`) with the Stock-Strategy-App via subdomain routing:
- `intraday-edge-4zz.uk` → `localhost:5180` (Stock-Strategy-App)
- `kimi.intraday-edge-4zz.uk` → `localhost:8190` (this app's Vite dev)

Public URL for phone/mobile access: **https://kimi.intraday-edge-4zz.uk**

The tunnel config lives at `C:\Users\phani\.cloudflared\config.yml`. When
changing the ingress, restart cloudflared with:
```powershell
Stop-Process -Name cloudflared -Force
cloudflared tunnel run intraday-edge
```

**After system restart:** cloudflared does NOT auto-start. To bring the
public URL back online:
```powershell
# 1. Start the backend (required for API/WS)
cd engine && uvicorn main:app --host 0.0.0.0 --port 8172 --reload

# 2. Start the frontend (required for dashboard UI)
cd frontend && npm run dev

# 3. Start the Cloudflare tunnel
cloudflared tunnel run intraday-edge
```
Then verify: `curl -s https://kimi.intraday-edge-4zz.uk/api/health`

The frontend WebSocket uses the relative path `/ws/v1/stream`
(`frontend/src/hooks/useWebSocket.ts:5`); Vite's `/ws` proxy forwards it to
`ws://localhost:8172`.

**WebSocket limitation:** Cloudflare tunnels do not proxy WebSocket traffic by default.
The frontend `useWebSocket` hook connects to `/ws/v1/stream`, which works locally
(`ws://localhost:8172/ws/v1/stream` returns `101 Switching Protocols`) but fails
through the public tunnel (`wss://kimi.intraday-edge-4zz.uk/ws/v1/stream`).

When WS fails, the dashboard falls back to REST polling (60s for rankings, 300s for context,
etc.). This is why MOCK badges persist — the REST endpoints return mock data when the
pipeline has no real rankings, and without WS there is no push of real L1/L6/L8/L10 events.

**To enable WS through the tunnel** (requires Cloudflare Zero Trust dashboard access):
1. In Cloudflare dashboard → Networks → Tunnels → `intraday-edge`
2. Add an additional public hostname: `kimi.intraday-edge-4zz.uk/ws/*`
3. Set service type to `HTTP` → `localhost:8172`
4. Under Additional application settings → HTTP → enable `No TLS Verify` if using self-signed certs
5. Under Connectivity → enable WebSocket support

## Architecture

NSE Intraday Trading Engine v1.2 — a **research-only** (Phase 1, no live order
execution) system that scores all 100 Nifty constituents every minute, ranks
the Top 25 long and short candidates, and emits thesis cards (entry,
invalidation, T1, T2) with full Indian-cost-aware net R:R.

### Pipeline: L1 → L10 (one file per layer in `engine/layers/`)

| Layer | File | Purpose |
|---|---|---|
| L1 | `l1_market_context.py` | Regime (3-state) + VIX band + breadth + time bucket |
| L2 | `l2_universe.py` | Per-stock flags (F&O ban, MWPL, earnings, LQS) |
| L3 | `l3_signals.py` | Indicators (EMA, ST, ADX, RSI, MACD, ATR, BB, VWAP), OI class, option Greeks |
| L4 | `l4_sector.py` | 11-sector RS-Ratio + RS-Momentum + rotation rank |
| L5 | `l5_scoring.py` | 7 factors × regime-conditional weights → score 0–100 |
| L6 | `l6_ranking.py` | Cross-sectional rank with hysteresis; tracks NEW/UP/DOWN/STABLE |
| L7 | `l7_confluence.py` | 6 mechanical pass/fail checks |
| L8 | `l8_thesis.py` | Assembles ThesisCard for 6 setup types, applies cost model + time-decay |
| L9 | `l9_monitor.py` | Shadow ledger state machine; tracks MFE/MAE/R-multiple per thesis |
| L10 | `l10_edge.py` | 6-tier hierarchical lookup with Wilson CI / BH FDR / Bayesian bootstrap |

The pipeline runs every minute under APScheduler; `engine/core/scheduler/`
holds the cron triggers and the NSE holiday calendar.

### API-Contract-First pattern

REST + WebSocket schemas (`models/frames.py` + `api/rest_routes.py` +
`api/websocket_manager.py`) were defined first with mock responses. Layer
implementations replace the mocks one-by-one. The frontend has always built
against the real contracts.

| Endpoint | Returns |
|---|---|
| `GET /health` | HealthResponse (WS state, token expiry, DB/Redis, scheduler jobs) |
| `GET /market/context` | MarketContextFrame (L1) |
| `GET /rankings/top25/{long\|short}` | `List[RankingEntry]` (L6) |
| `GET /thesis/{id}` | ThesisCard (L8) |
| `GET /thesis/{id}/outcome` | `ThesisOutcome \| None` (L9) |
| `GET /edge/tiers` and `/edge/tier/{id}/stats` | EdgeTierStats (L10) |
| `WS /ws/v1/stream` | Subscribe channels `market`/`rankings`/`theses`/`edge`; server pushes `L1_CONTEXT`, `L6_RANKINGS`, `L8_THESIS`, `L9_INVALIDATION`, `L10_EDGE` |

### Data layer

- **Upstox API v3** is the only data source. Phase 1 needs only the
  **Analytics Token** (1-year validity, no daily OAuth login).
  `engine/core/data/upstox_rest.py` and `upstox_ws.py`. WebSocket runs two
  connections: 100 stocks in Full mode + ~20 indices in LTPC.
- **TimescaleDB** (PostgreSQL 15 + Timescale extension) holds hypertables for
  `market_bars`, `thesis_outcomes`, and a continuous aggregate
  `edge_stats_daily`. Migrations are plain SQL in `engine/db/migrations/`.
- **Redis** is the real-time state store (market context, top25 sorted sets,
  active theses, L10 tier hashes). Key shapes documented in
  `docs/superpowers/specs/2026-05-16-intraday-dashboard-mvp1-design.md`.
- **NSE scraper** (`core/data/nse_scraper.py`) fetches F&O ban list, MWPL,
  earnings, corporate actions at 08:00 IST daily.

### Frontend state

- **Zustand** (`stores/marketStore.ts`) — WS-pushed state (context, rankings, etc.)
- **TanStack Query** — REST cache for non-streaming reads
- **Native WebSocket** in `hooks/useWebSocket.ts` writes to the Zustand store
- **PWA** via `vite-plugin-pwa` (autoUpdate, no custom manifest yet)

## Verifying the system is working

### Quick health check
```powershell
# Check backend health
curl http://localhost:8170/health

# Check frontend builds
cd frontend && npm run build

# Run tests
pytest tests/test_l1.py tests/test_l6.py tests/test_l8.py tests/test_l10.py

# Run integration test
pytest tests/test_pipeline.py -v
```

### Start the full stack
```powershell
# Terminal 1: Backend (requires .env with Upstox token)
cd engine
uvicorn main:app --host 0.0.0.0 --port 8170 --reload

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3 (optional): Docker services
docker compose up -d
```

Then open http://localhost:8190 in a browser. You should see:
- RegimeBanner with current market regime
- Top 25 long/short tables with scores and factors
- Pipeline status showing L1-L10 stages
- Real-time updates via WebSocket

## Authoritative design documents

When in doubt about algorithm details, behavior, or rationale, consult these
in order:

1. `system_design_final.md` — the canonical, finalized system design (L1–L10
   algorithm specifics, cost model, expiry rules, edge statistics math).
2. `docs/superpowers/specs/2026-05-16-intraday-dashboard-mvp1-design.md` —
   MVP 1 scope, API contract, DB schema, Redis keys, port assignments.
3. `docs/superpowers/plans/2026-05-17-mvp1-complete-closure-v2.md` —
   latest implementation completion checklist.
4. `Intraday_Engine_Algorithm_v1_2.pdf` — the underlying algorithm spec.

Do not re-derive algorithm details by reading layer code alone; the design docs
encode constants, thresholds, and the "why" that the code does not.

## MVP 1 Completion Status (as of 2026-05-17)

### ✅ Fully Implemented

**Backend (Engine)**
- ✅ All 10 layers (L1-L10) implemented with real algorithms
- ✅ Pipeline orchestration: TickBuffer, BarAggregator, PipelineOrchestrator
- ✅ FastAPI main.py with lifespan management (scheduler startup/shutdown)
- ✅ REST routes: `/health`, `/market/context`, `/rankings/top25/{long|short}`, `/thesis/{id}`, `/edge/tiers`, `/pipeline/status`
- ✅ WebSocket manager with L1/L6/L8/L9/L10 broadcast channels
- ✅ Upstox REST and WebSocket client (2 connections: Full + LTPC modes)
- ✅ NSE scraper (F&O ban list, MWPL, earnings)
- ✅ Redis cache layer (market context, top25 sets, active theses, L10 tiers)
- ✅ TimescaleDB migrations and schema
- ✅ Market session awareness (09:15-15:30 IST, NSE holidays)
- ✅ Telegram alerts integration
- ✅ Token manager (OAuth tracking)

**Frontend (React)**
- ✅ Vite build with TypeScript strict mode
- ✅ Core components: RegimeBanner, Top25Table, ThesisCard, ActiveMonitor, EdgePanel
- ✅ Advanced components: FactorGrid, RankingRowExpanded, ScoreBreakdown, ConfluenceChecklist, DataAgeBadge, PipelineStatusBar, ChartPanel
- ✅ Hooks: useWebSocket, useRankings, useMarketContext, useDataAge, usePipelineStatus, useFactorBreakdown
- ✅ Zustand store (marketStore) with full L1-L10 state
- ✅ TanStack Query for REST caching
- ✅ Tailwind CSS styling
- ✅ PWA setup (offline cache, installable)
- ✅ Comprehensive component tests (Vitest + jsdom)

**Testing**
- ✅ Unit tests for L1-L10 layers
- ✅ Integration tests: pipeline orchestration, WebSocket broadcasts
- ✅ Factor breakdown API tests
- ✅ Pipeline status endpoint tests
- ✅ E2E smoke tests
- ✅ No Python deprecation warnings (fixed `datetime.utcnow()`)

**Docker & DevOps**
- ✅ docker-compose.yml with 4 services (engine, timescaledb, redis, caddy)
- ✅ Port mappings: 8170 (engine), 8150 (DB), 8160 (redis), 8190 (Vite dev), 8180 (web)
- ✅ .env.example template with required credentials

### ⚠️ Phase 1 Constraints (Honored)
- ✅ **No live order execution** — L9 is shadow ledger only
- ✅ **All 100 Nifty constituents scored** every minute (no premature filtering)
- ✅ **Net R:R includes full Indian costs** (STT, GST, brokerage, slippage)

### 📋 Known Limitations (Phase 2+)
- No OAuth token refresh (Analytics Token valid 1 year)
- No paper trading simulation
- No OpenAlgo integration
- WebSocket reconnect: fixed backoff (not adaptive)
- No push notifications (Web Push API)

## Phase 1 invariants (do not violate)

- **No live order execution.** L9 is a shadow ledger; never call Upstox order
  endpoints. The OAuth refresh path is out of scope until Phase 2.
- **No stock exclusion at scoring.** All 100 Nifty constituents are scored
  every minute. Filtering happens at the actionability-tier layer, not the
  scoring layer.
- **Net R:R must include full Indian costs.** STT, exchange, SEBI, stamp,
  GST, brokerage, and depth-derived slippage — see `l8_thesis.py` and the
  cost-model section of `system_design_final.md`.

## Development branch workflow

When working on a new feature or bugfix:

1. **Option A: Direct branch** (simpler, for small changes)
   ```powershell
   git checkout -b feat/my-feature
   # Make changes, test, commit
   git push
   ```

2. **Option B: Worktree isolation** (recommended for large refactors)
   ```powershell
   git worktree add .worktrees/feat-name
   # Work in isolation, test, commit
   git push
   git worktree remove .worktrees/feat-name
   ```
   
   Use `superpowers:using-git-worktrees` skill for structured worktree workflow.
