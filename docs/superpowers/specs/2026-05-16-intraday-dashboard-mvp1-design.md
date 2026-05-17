# Intraday Dashboard — MVP 1 Design

**Scope:** Research-Only Engine + React PWA Dashboard
**Date:** 2026-05-16
**Approach:** API-Contract First
**Stack:** FastAPI + Polars + TimescaleDB + Redis + React 18 + Upstox API v3

---

## 1. Architecture

```
React PWA (Vite + TS + Tailwind + Zustand + TanStack Query)
    ↑↓ WS /ws/v1/stream
    ↑↓ REST /api/v1/*
FastAPI Engine (Uvicorn + APScheduler)
    ├── API Layer (contracts first, mocks → real)
    ├── L1 Market Context
    ├── L2 Universe Enrichment
    ├── L3 Per-Stock Signals
    ├── L4 Sector Context
    ├── L5 Multi-Factor Scoring (Polars)
    ├── L6 Cross-Sectional Ranking
    ├── L7 Mechanical Confluence
    ├── L8 Thesis Assembly
    ├── L9 Shadow Ledger
    └── L10 Hierarchical Edge Lookup
TimescaleDB (hypertables + continuous aggregates)
Redis (real-time state + pub/sub)
Upstox API v3 (REST + 2x WebSocket)
```

**Key principle:** API endpoints and Pydantic/WebSocket models are defined on day one. Backend layers replace mock responses incrementally. Frontend builds against real contracts immediately.

---

## 2. MVP 1 Scope

### In Scope
- Docker Compose stack (engine, timescaledb, redis, web)
- Upstox REST client: historical bars, analytics (OI/PCR/max-pain), charges preview
- Upstox WebSocket client: 2 connections (100 stocks Full + indices LTPC)
- NSE scraper: F&O ban list, MWPL, earnings, corporate actions
- L1-L8 full pipeline running every minute
- L9 Shadow Ledger: theoretical entry/exit tracking, MFE/MAE, state machine
- L10 Edge Lookup: 6-tier fallback, Wilson CI, Benjamini-Hochberg FDR, Bayesian bootstrap
- React PWA: regime banner, Top 25 tables, thesis cards, active monitor, edge panel
- WebSocket live updates for rankings, theses, invalidations
- Telegram alerts: engine start, regime change, thesis triggered/exit, WS drops, critical failures
- Health endpoint + structured logging (structlog)
- NSE holiday handling

### Out of Scope
- OAuth / live order execution (MVP 2+)
- Paper trading (MVP 2)
- OpenAlgo integration (MVP 3)
- Advanced Polars performance tuning (deferred to Polish phase)
- Push notifications via Web Push API (deferred)

---

## 3. API Contract

### REST Endpoints

| Method | Path | Response Model | Purpose |
|---|---|---|---|
| GET | `/health` | `HealthResponse` | Status, WS state, token expiry, DB/Redis connectivity |
| GET | `/market/context` | `MarketContextFrame` | L1 regime, VIX, breadth, time bucket, premarket bias |
| GET | `/rankings/top25/{direction}` | `RankingResponse` | L6 Top 25 long or short with movement flags |
| GET | `/thesis/{thesis_id}` | `ThesisCard` | L8 full thesis: trigger, invalidation, T1, T2, net R:R, tier |
| GET | `/thesis/{thesis_id}/outcome` | `ThesisOutcome \| None` | L9 metrics if terminal (MFE, MAE, net return, R-multiple) |
| GET | `/edge/tiers` | `EdgeTiersResponse` | L10 active tiers + recent promotion events |
| GET | `/edge/tier/{tier_id}/stats` | `EdgeTierStats` | Specific tier: n, hit_rate, wilson_ci, is_significant |

### WebSocket Protocol

Client subscribes via:
```json
{"action": "subscribe", "channels": ["market", "rankings", "theses", "edge"]}
```

Server messages:
| Type | Payload | Frequency |
|---|---|---|
| `L1_CONTEXT` | `MarketContextFrame` | Every 5 min (or on regime change) |
| `L6_RANKINGS` | `{long: RankingEntry[], short: RankingEntry[]}` | Every minute |
| `L8_THESIS` | `{thesis_id: str, card: ThesisCard}` | On creation / update |
| `L9_INVALIDATION` | `{thesis_id: str, reason: str}` | On invalidation event |
| `L10_EDGE` | `{tier: int, promotion: str}` | On tier promotion |

### Core Pydantic Models

- `MarketContextFrame` — regime (enum), regime_confidence, volatility_qualifier, vix_band, vix_trajectory, time_bucket, event_flag, breadth, premarket_bias, bank_nifty_divergence
- `RankingEntry` — symbol, instrument_key, score, setup_type, confluence_score, net_rr, actionability_tier, rank_movement (NEW/UP/DOWN/STABLE), liquidity_quality
- `ThesisCard` — thesis_id, symbol, direction, setup_type, trigger, invalidation, t1, t2, gross_rr, net_rr, grade, time_decay_multiplier, actionability_tier, valid_until, preferred_regime
- `ThesisOutcome` — thesis_id, state (enum), entry_ts, exit_ts, entry_price, exit_price, mfe_pct, mae_pct, gross_return_pct, net_return_pct, r_multiple, time_to_trigger_min, time_to_exit_min
- `EdgeTierStats` — tier_id, setup_type, regime, sector, time_bucket, direction, n, hit_rate, ci_lower, ci_upper, is_significant, avg_net_return, std_net_return

---

## 4. Database Schema

### Hypertables

**`market_bars`**
```sql
CREATE TABLE market_bars (
    time TIMESTAMPTZ NOT NULL,
    instrument_key TEXT NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume BIGINT,
    oi BIGINT,
    vwap DOUBLE PRECISION,
    PRIMARY KEY (time, instrument_key)
);
SELECT create_hypertable('market_bars', 'time');
```

**`thesis_outcomes`**
```sql
CREATE TABLE thesis_outcomes (
    time TIMESTAMPTZ NOT NULL,
    thesis_id UUID,
    symbol TEXT,
    direction TEXT,
    setup_type INT,
    regime INT,
    sector INT,
    time_bucket INT,
    hit BOOLEAN,
    gross_return_pct DOUBLE PRECISION,
    net_return_pct DOUBLE PRECISION,
    mfe_pct DOUBLE PRECISION,
    mae_pct DOUBLE PRECISION,
    r_multiple DOUBLE PRECISION,
    time_to_trigger_min INT,
    time_to_exit_min INT,
    confluence_score INT,
    score_at_creation INT,
    liquidity_quality TEXT
);
SELECT create_hypertable('thesis_outcomes', 'time');
```

### Continuous Aggregate

**`edge_stats_daily`**
```sql
CREATE MATERIALIZED VIEW edge_stats_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) as day,
    setup_type, regime, sector, time_bucket as tb, direction,
    COUNT(*) as n,
    AVG(hit::int) as hit_rate,
    AVG(net_return_pct) as avg_net_return,
    STDDEV(net_return_pct) as std_net_return
FROM thesis_outcomes
GROUP BY 1, 2, 3, 4, 5, 6;
```

### Static Tables

- `instruments` — symbol, instrument_key, segment, isin, lot_size, tick_size, fo_eligible
- `nse_flags` — symbol, date, fo_ban, mwpl_status, earnings_flag, circuit_limit
- `volume_seasonality` — symbol, time_bucket, avg_volume_10d, std_volume_10d
- `session_calendar` — date, is_trading_day, is_expiry, event_flag

### Redis Key Structure

```
market:context → JSON (L1 frame)
market:global_cues → JSON (SGX, Dow, Brent, USDINR)

universe:{symbol} → Hash (L2 flags)
universe:ban_list → Set
universe:earnings_today → Set

bars:latest:{instrument_key} → Hash (last 1-min OHLCV + OI)
bars:session:{instrument_key} → Sorted Set (ticks for VWAP)

top25:long → Sorted Set (score → symbol)
top25:short → Sorted Set (score → symbol)
top25:movement:{symbol} → String (NEW/UP/DOWN/STABLE)

thesis:{thesis_id} → Hash (full card)
thesis:active → Set (active IDs)
thesis:invalidation:{thesis_id} → Hash (conditions)

l10:tier:{tier}:{setup}:{regime}:{sector}:{tb}:{dir} → Hash (stats)
```

---

## 5. Frontend Structure

### Component Hierarchy

```
App.tsx
├── RegimeBanner.tsx          ← L1 context display
├── DashboardGrid.tsx
│   ├── Top25Table.tsx         ← L6 long/short with movement
│   │   └── RankingRow.tsx
│   ├── ThesisPanel.tsx
│   │   ├── ThesisCard.tsx     ← L8 detail view
│   │   └── ThesisMini.tsx     ← inline preview
│   ├── ActiveMonitor.tsx      ← L9 live state machine
│   └── EdgePanel.tsx          ← L10 tier stats
└── AlertToast.tsx             ← WS invalidations
```

### State Management

- **Zustand:** UI state (selected thesis, sidebar open/close, theme)
- **TanStack Query:** Server state (REST endpoints with caching/refetching)
- **Native WebSocket:** Real-time streams write to a Zustand slice that components subscribe to

### PWA Features

- Vite PWA plugin for service worker + manifest
- Offline cache for static assets + last known rankings
- Installable (add to home screen)

---

## 6. Build Order (MVP 1)

### Phase A: Contracts + Scaffolding
1. Docker Compose (engine, timescaledb, redis, web)
2. FastAPI app shell with lifespan management
3. Pydantic models (`frames.py`, `enums.py`)
4. REST routes with mock responses
5. WebSocket manager with mock broadcasts
6. React scaffold (Vite + TS + Tailwind + Zustand + TanStack Query)
7. Frontend fetches mocks, basic layout renders

### Phase B: Data Ingestion
8. Upstox REST client (httpx async): historical bars, analytics, charges
9. Upstox WebSocket client (websockets + protobuf): connect, reconnect, parse
10. NSE scraper (ban list, MWPL, earnings)
11. Redis cache layer
12. TimescaleDB connection + migration runner

### Phase C: Engine Layers
13. L1 Market Context (regime, VIX, breadth)
14. L2 Universe Enrichment (flags, LQS)
15. L3 Per-Stock Signals (indicators, volume, OI, options)
16. L4 Sector Context (RS-Ratio, RS-Momentum)
17. L5 Multi-Factor Scoring (Polars, regime-conditional weights)
18. L6 Cross-Sectional Ranking (hysteresis, movement tracking)
19. L7 Mechanical Confluence (6 checks)
20. L8 Thesis Assembly (6 setups, cost model, time-decay)

### Phase D: Outcome + Edge
21. L9 Shadow Ledger (state machine, MFE/MAE tracking)
22. L10 Edge Lookup (6 tiers, Wilson CI, BH FDR, Bayesian bootstrap)
23. Continuous aggregate refresh pipeline

### Phase E: Polish
24. Telegram alerts integration
25. Health checks + monitoring
26. NSE holiday handling
27. Error recovery + circuit breakers
28. Frontend polish (charts, responsive, PWA install)

---

## 7. Error Handling & Resilience

| Failure | Behavior | Alert |
|---|---|---|
| WS disconnect | Auto-reconnect with exponential backoff (5 retries) | WARN after 2nd retry, CRITICAL after 5 |
| Upstox rate limit | Exponential backoff + request queue priority | WARN |
| Analytics token expiry (<7 days) | Log + Telegram daily reminder | INFO |
| NSE scraper fail (8 AM) | Retry 3×, fallback to yesterday's data | WARN if still failing |
| Polars compute > 1 min | Log timing, alert if recurring | WARN |
| DB connection lost | Reconnect with 3 retries, queue writes to Redis | CRITICAL if permanent |
| Redis connection lost | Reconnect, degrade to in-memory cache | WARN |
| Holiday | Skip market jobs, log sleep message | INFO daily |

---

## 8. Testing Strategy

- **Unit:** Each L1-L8 layer tested in isolation with fixture data (pytest)
- **Integration:** FastAPI TestClient for REST + WS contracts
- **Data validation:** Pydantic strict mode on all frames
- **Mock Upstox:** `respx` for httpx, custom WS mock for protobuf feed
- **Frontend:** Vitest for component rendering, MSW for API mocking
- **E2E smoke:** Health endpoint passes, WS connects, 1-min bar pipeline completes

---

## 9. Deployment

- Docker Compose on VPS (Mumbai region for <5ms NSE latency)
- Caddy reverse proxy (automatic HTTPS)
- `.env` for secrets (Analytics Token, DB password, Telegram credentials)
- Persistent volumes: engine_data, tsdb_data, redis_data, caddy_data
- Healthcheck on engine container

## 10. Port Assignments

| Service | Container Port | Host Port | Status |
|---|---|---|---|
| FastAPI Engine | 8000 | **8084** | Available (8000/8001/8083 taken) |
| TimescaleDB | 5432 | **5433** | Available (5432/15432 taken) |
| Redis | 6379 | **6380** | Available (6379 taken by Docker Redis) |
| React Vite Dev | 5173 | **5174** | Available (5173/5180/5181 taken) |
| WebSocket | 8000 | **8084** | Upgrades from same FastAPI port |
| Visual Companion | — | 63394 | Already running (brainstorming) |

**Rationale:** Existing services (postgres on 5432, Redis on 6379, python on 8000/8001, node on 5173/5180/5181) are left untouched. Docker Compose maps to alternative host ports for full isolation.

---

**END OF DESIGN**
