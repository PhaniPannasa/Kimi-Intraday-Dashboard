# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Where the code actually lives

The root of this repo is intentionally near-empty: it only tracks design docs
(`system_design_final.md`, `Intraday_Engine_Algorithm_v1_2.pdf`,
`docs/superpowers/`). **All application code lives in `.worktrees/mvp1/`**,
which is `.gitignore`d at the root and is itself a separate git worktree.

When asked to find, build, run, or test code, `cd .worktrees/mvp1/` first.

```
.worktrees/mvp1/
├── docker-compose.yml         # 4-service stack
├── .env.example               # required env vars
├── engine/                    # FastAPI backend (Python 3.11)
│   ├── main.py                # ASGI entrypoint
│   ├── config.py              # pydantic-settings
│   ├── pyproject.toml         # deps + setuptools config
│   ├── api/                   # rest_routes.py, websocket_manager.py
│   ├── core/                  # data/ (upstox_rest, upstox_ws, nse_scraper, redis_cache),
│   │                          # scheduler/ (market_scheduler, holidays), alerts/ (telegram)
│   ├── layers/                # l1_market_context … l10_edge (one file per L-layer)
│   ├── models/                # enums.py, frames.py (Pydantic v2)
│   └── db/                    # timescale.py + migrations/*.sql
├── frontend/                  # React 18 + Vite + TS PWA
│   └── src/{App.tsx, components/, hooks/, stores/, types/, lib/}
└── tests/                     # pytest, mirrors L1–L10 + integration + e2e/
```

## Common commands

All commands assume cwd `.worktrees/mvp1/`.

### Backend (FastAPI engine)

```powershell
# Install deps (editable, with test extras)
pip install -e "engine[.test]"

# Run dev server (auto-reload on :8000 inside, :8084 outside Docker)
cd engine; uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# All tests
pytest

# Single test file or test
pytest tests/test_l5.py
pytest tests/test_l5.py::test_score_clamping

# E2E smoke (hits the live ASGI app via httpx)
pytest tests/e2e/
```

`pytest.ini` sets `asyncio_mode = auto` — do NOT add `@pytest.mark.asyncio`;
`async def test_*` is picked up automatically. `tests/conftest.py` inserts
`engine/` into `sys.path` so `from main import app` works without packaging.

### Frontend (React PWA)

```powershell
cd frontend
npm install
npm run dev        # Vite on :5174, proxies /api → http://localhost:8084
npm run build      # tsc + vite build → dist/
npm test           # vitest (jsdom, setup in src/test-setup.ts)
```

### Full stack via Docker Compose

```powershell
docker compose up -d           # engine + timescaledb + redis + web
docker compose logs -f engine
docker compose down
```

## Port mapping (non-obvious — host ports differ from container ports)

Host ports are shifted because the dev machine already runs other services on
the canonical ports. Use these when hitting the stack from the host:

| Service        | Container | Host  | Why shifted                |
|----------------|-----------|-------|----------------------------|
| FastAPI engine | 8000      | 8084  | 8000/8001 used by other py |
| TimescaleDB    | 5432      | 5433  | 5432 used by host postgres |
| Redis          | 6379      | 6380  | 6379 used by other docker  |
| Caddy / web    | 80        | 8080  | —                          |
| Vite dev       | —         | 5174  | proxies `/api` → :8084     |

The frontend WebSocket URL is hard-coded to `ws://localhost:8084/ws/v1/stream`
in `frontend/src/hooks/useWebSocket.ts`.

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

## Authoritative design documents

When in doubt about algorithm details, behavior, or rationale, consult these
in order:

1. `system_design_final.md` — the canonical, finalized system design (L1–L10
   algorithm specifics, cost model, expiry rules, edge statistics math).
2. `docs/superpowers/specs/2026-05-16-intraday-dashboard-mvp1-design.md` —
   MVP 1 scope, API contract, DB schema, Redis keys, port assignments.
3. `docs/superpowers/plans/2026-05-16-intraday-dashboard-mvp1.md` —
   task-by-task implementation plan (the script the MVP was built from).
4. `Intraday_Engine_Algorithm_v1_2.pdf` — the underlying algorithm spec.

Do not re-derive algorithm details by reading layer code alone; the design docs
encode constants, thresholds, and the "why" that the code does not.

## Phase 1 invariants (do not violate)

- **No live order execution.** L9 is a shadow ledger; never call Upstox order
  endpoints. The OAuth refresh path is out of scope until Phase 2.
- **No stock exclusion at scoring.** All 100 Nifty constituents are scored
  every minute. Filtering happens at the actionability-tier layer, not the
  scoring layer.
- **Net R:R must include full Indian costs.** STT, exchange, SEBI, stamp,
  GST, brokerage, and depth-derived slippage — see `l8_thesis.py` and the
  cost-model section of `system_design_final.md`.

## Worktree workflow

This project uses git worktrees for isolated development. `.worktrees/mvp1/`
is one such worktree (its own `.git` file points back to the main repo). When
creating a new development branch, prefer adding a new worktree under
`.worktrees/<branch-name>/` over mutating `.worktrees/mvp1/`. The
`superpowers:using-git-worktrees` skill covers the setup.
