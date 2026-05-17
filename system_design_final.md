# NSE Intraday Trading Engine v1.2 — System Design Document

**Version:** 1.0  
**Date:** 2026-05-16  
**Stack:** Python FastAPI + Polars + TimescaleDB + Redis + React PWA + Upstox API v3  
**Status:** FINALIZED — Ready for implementation

---

## 1. Executive Summary

This document specifies the complete technical architecture for the NSE Intraday Trading Engine v1.2 algorithm. The system is **fully automated, self-hosted, and requires zero daily manual intervention** after initial deployment.

**Key Principles:**
- **Research-Only:** No live order execution in Phase 1. L9 uses an internal shadow ledger.
- **No Exclusion:** All 100 Nifty constituents scored every minute.
- **Honest Economics:** Every thesis displays net R:R after full Indian transaction costs.
- **Self-Healing:** Auto-reconnect, auto-refresh, auto-scheduling with Telegram alerting.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    REACT PWA (Frontend)                      │
│         Port 80/443 — Nginx + Vite + Tailwind               │
│         WebSocket to Engine for live updates                  │
└─────────────────────────────────────────────┬─────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────┐
│              FASTAPI ENGINE (Backend)                       │
│         Port 8000 — Python + Uvicorn + APScheduler          │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │  L1-L8      │  │  L9 Shadow  │  │  L10 Edge Lookup    │   │
│  │  Compute    │  │  Ledger     │  │  (TimescaleDB)      │   │
│  │  (Polars)   │  │  (Tick-based│  │  (Wilson CI/BH)      │   │
│  └─────────────┘  └─────────────┘  └─────────────────────┘   │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │  Scheduler  │  │  Token Mgr  │  │  Alert Manager      │   │
│  │  (APSched)  │  │  (Auto-ref) │  │  (Telegram)         │   │
│  └─────────────┘  └─────────────┘  └─────────────────────┘   │
└─────────────────────────────────────────────┬─────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
                    ▼                         ▼                         ▼
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│   UPSTOX API v3      │    │   TIMESCALEDB        │    │   REDIS              │
│   (Data Ingestion)   │    │   (Persistent)       │    │   (Real-time State)  │
│                      │    │                      │    │                      │
│  • REST: Historical  │    │  • 1-min bars        │    │  • Market Context    │
│  • REST: Analytics   │    │  • Thesis outcomes   │    │  • Top 25 Rankings   │
│  • REST: Charges     │    │  • Edge statistics   │    │  • Active Theses     │
│  • WS: Live ticks    │    │  • Volume profiles   │    │  • Session Flags     │
│  • WS: Market depth  │    │  • Seasonality       │    │  • Invalidation      │
└──────────────────────┘    └──────────────────────┘    └──────────────────────┘
```

---

## 3. Technology Stack

### Backend
| Component | Technology | Purpose |
|---|---|---|
| API Framework | FastAPI + Uvicorn | Async REST + WebSocket |
| Computation | Polars | L5-L6 cross-sectional scoring (100 stocks × 7 factors) |
| Indicators | Custom NumPy + Pandas-TA | EMA, Supertrend, ADX, RSI, MACD, ATR, Bollinger |
| Stats | SciPy + NumPy | Wilson CI, Bayesian bootstrap, Benjamini-Hochberg |
| Scheduler | APScheduler (asyncio) | 1-min/5-min/15-min/23:00 cron triggers |
| DB | TimescaleDB (PostgreSQL 15) | Time-series hypertables for bars, outcomes, edge |
| Cache | Redis | Real-time state pub/sub |
| HTTP Client | httpx (async) | Upstox REST API calls |
| WS Client | websockets (async) | Upstox protobuf feed |
| Validation | Pydantic v2 | Strict typing for all frames and thesis cards |
| Logging | Structlog | JSON structured logs for audit |

### Frontend
| Component | Technology | Purpose |
|---|---|---|
| Framework | React 18 + TypeScript | Strict typing for complex thesis structures |
| PWA | Vite PWA Plugin | Service worker, offline cache, installable |
| State | Zustand | Lightweight real-time WS state |
| Charts | Lightweight Charts™ (TradingView) | Professional financial charting |
| UI | Shadcn/ui + Tailwind CSS | Thesis cards, regime badges, data tables |
| Tables | TanStack Table | Virtualized Top 25 with rank movement |
| Real-time | Native WebSocket | Engine WS connection |

### Infrastructure
| Component | Technology | Purpose |
|---|---|---|
| Reverse Proxy | Caddy | Automatic HTTPS, reverse proxy |
| Container | Docker + Docker Compose | 3-service stack |
| VPS | Mumbai region (AWS/DigitalOcean) | <5ms latency to NSE |
| Alerts | Telegram Bot API | Critical failure + daily summary |

---

## 4. Upstox API Integration Map

### Authentication
| Token Type | Source | Validity | Use For |
|---|---|---|---|
| **Analytics Token** | Developer Console | **1 year** | Historical data, WebSocket, quotes, option chain, charges preview |
| OAuth Access Token | Login flow | ~1 day (expires 3:30 AM) | Order execution (Phase 2 only) |
| OAuth Refresh Token | Login flow | Multi-month | Auto-refresh access token at 3:35 AM |

**Phase 1 (Research):** Only Analytics Token needed. Zero daily login.

### REST Endpoints Used
| Your Layer | Upstox Endpoint | Token | Frequency |
|---|---|---|---|
| L1 Global Cues | `GET /v3/historical-candle/intraday/{GLOBAL_INDEX\|SGX NIFTY,...}/minutes/5` | Analytics | Daily 6:00 AM |
| L1 Regime | `GET /v3/historical-candle/intraday/{NSE_INDEX\|Nifty 50}/minutes/5` | Analytics | Every 5 min |
| L3 Signals | `GET /v3/historical-candle/intraday/{NSE_EQ\|SYMBOL}/minutes/1` | Analytics | Backfill at 9:15 AM |
| L3 OI/PCR | `GET /v2/option/chain` | Analytics | Every 15 min |
| L3 Analytics | `GET /v2/market/oi`, `/change-in-oi`, `/max-pain`, `/pcr` | Analytics | Every 15 min |
| L8 Cost Model | `GET /v2/charges/brokerage` | Analytics | Per thesis (or hardcoded) |
| L9 Order Status | `GET /v2/order/details`, `/trades` | OAuth (Phase 2) | On trigger |

### WebSocket Subscriptions
| Connection | Mode | Instruments | Purpose |
|---|---|---|---|
| WS-1 | **Full** | 100 Nifty stocks | LTP, volume, OI, 5-level depth, circuit limits |
| WS-2 | **LTPC** | Nifty 50, BankNifty, India VIX, 11 sector indices | Lightweight index tracking |

**Total:** 120 instruments across 2 connections (within Upstox limits).

---

## 5. Layer-by-Layer Implementation

### L1: Market Context Layer
**File:** `engine/layers/l1_market_context.py`

**Inputs:**
- Nifty 50 5-min bars (Upstox REST)
- BankNifty 5-min bars (Upstox REST)
- India VIX (Upstox REST)
- Global cues: GIFT Nifty, Dow, Brent, USDINR (Upstox REST, 6:00 AM only)
- Market breadth (computed from WS-1 100-stock feed)
- Time bucket (system clock)

**Computation:**
```python
# Regime Classification (3-State)
# Step 1: 20-bar realized volatility on 5-min Nifty 50
# Step 2: Volatility z-score vs 60-day baseline
# Step 3: 50-bar EMA slope
# Step 4: Classify Trending-Up / Trending-Down / Range-Bound

# Cold-start (9:15-10:45): 9-bar EMA on 15-min bars
# Transition to primary 50-bar 5-min system at 10:45 AM

# VIX Bands (Dynamic)
# <20th percentile trailing 90 days = Compressed
# 20th-80th = Normal
# >80th = Elevated

# Breadth (Computed)
# B = 0.5×VWAP_pct + 0.25×A_D_ratio + 0.25×H_L_ratio
# Strong >0.60, Mixed 0.40-0.60, Weak <0.40
```

**Output (Market Context Frame):**
```json
{
  "regime": "Trending-Up",
  "regime_confidence": 0.85,
  "volatility_qualifier": "Volatile",
  "vix_band": "Elevated",
  "vix_trajectory": "Rising",
  "time_bucket": "Trend Establishment",
  "event_flag": null,
  "breadth": "Strong",
  "premarket_bias": "Positive",
  "bank_nifty_divergence": 0.0
}
```

### L2: Universe Enrichment Layer
**File:** `engine/layers/l2_universe.py`

**Sources:**
- Upstox Instrument Master (daily download)
- NSE scraper (8:00 AM cron): F&O ban list, MWPL, earnings, corporate actions
- Upstox WS `ExtendedFeedDetails`: `uc`, `lc` (live circuit limits)

**Flags per stock:**
```json
{
  "symbol": "RELIANCE",
  "instrument_key": "NSE_EQ|INE002A01018",
  "fo_eligible": true,
  "fo_ban": false,
  "mwpl_proximity": "None",
  "circuit_proximity": "None",
  "earnings_flag": "None",
  "index_change": "None",
  "stale_data": false,
  "liquidity_quality": "Excellent",
  "shortability": "FUTURES_OPTIONS"
}
```

**Liquidity Quality Score (LQS):**
```
D_norm = percentile_rank(top-5 bid+ask depth in Rs. lakhs)
S_norm = 1 - percentile_rank(bid-ask spread %)
T_norm = percentile_rank(10-day avg daily turnover in Rs. crores)
LQS = 0.4×D_norm + 0.35×S_norm + 0.25×T_norm
Buckets: Excellent (≥0.80), Good (0.55-0.79), Marginal (0.30-0.54), Poor (<0.30)
```

### L3: Per-Stock Signal Layer
**File:** `engine/layers/l3_signals.py`

**Indicators (all refreshed every 1-min bar close):**

| Indicator | Parameters | Timeframe | Output |
|---|---|---|---|
| EMA Stack | EMA(9), EMA(20), EMA(50) | 5-min + 15-min | Binary: aligned/mixed |
| Supertrend | ATR(10) × 3.0 | 5-min | Direction + distance to flip |
| ADX | ADX(14) | 5-min + 15-min | 0-100; >25 = trending |
| RSI | RSI(14) | 5-min + 15-min | 0-100; <30 oversold, >70 overbought |
| MACD Histogram | EMA(12,26,9) | 15-min | Value + direction |
| ROC vs Nifty | 20-bar ROC | 5-min | Stock return - Nifty return |
| ATR | ATR(14) | 5-min + 15-min | Absolute value |
| ATR Percentile | ATR vs 20-day dist | 5-min | Percentile rank |
| Bollinger Bands | SMA(20) ± 2σ | 5-min | Bandwidth + position |
| Volume | Seasonally-adjusted | 5-min | z-score vs 10-day profile |
| VWAP | Computed from ticks | Session | Position + sigma bands |

**MACD Divergence (Mechanical):**
```python
# Bullish (Long): Price 5-bar lower low AND MACD histogram 5-bar higher low
# Bearish (Short): Price 5-bar higher high AND MACD histogram 5-bar lower high
# Both confirmed by bar close. No human interpretation.
```

**Volume Seasonality:**
```python
# Step 1: Compute average volume per 5-min bucket over trailing 10 days
# Step 2: V_adj = V_raw / V_seasonal(t)
# Step 3: z_v = (V_adj - μ) / σ
# Step 4: V_confirm = V_adj >= 1.5 × median adjusted volume
```

**Reference Levels (computed at 9:15 AM, fixed for session):**
- PDH, PDL, PDC, CP, BC, TC
- Floor R1/R2/R3, S1/S2/S3
- ORB 15-min H/L, ORB 2-hour H/L
- First Hour H/L

**Open Interest Classification (F&O only, 15-min smoothing):**
| Price Change | OI Change | Classification |
|---|---|---|
| Rising (>+0.5%) | Increasing (>+2%) | Long Buildup |
| Falling (<-0.5%) | Increasing (>+2%) | Short Buildup |
| Falling (<-0.5%) | Decreasing (<-2%) | Long Unwinding |
| Rising (>+0.5%) | Decreasing (<-2%) | Short Covering |

**Options-Derived Signals (F&O only):**
- IV Percentile (60-day + 1-year)
- Expected Range: ATM ± (IV/√252) × ATM
- PCR Z-Score (20-day + 1-year)
- RV/IV Ratio

### L4: Sector Context Layer
**File:** `engine/layers/l4_sector.py`

**11 Sectors:** Auto, Bank, FMCG, IT, Media, Metal, Pharma, PSU Bank, Realty, Energy, Telecom

**Computation:**
```python
# Step 1: 5-day and 20-day returns for each sector index vs Nifty 50
# Step 2: RS-Ratio = (R_sector / R_Nifty) / 60-day rolling std dev
# Step 3: RS-Momentum = 5-day change in RS-Ratio
# Step 4: Rank all 11 sectors, track rank change over 30 min
# Step 5: Rotation: Gaining (+2 ranks), Steady (±1), Losing (-2 ranks)
```

### L5: Multi-Factor Scoring Layer
**File:** `engine/layers/l5_scoring.py`

**Seven Factor Sub-Scores (0-100 each):**

| Factor | Components | Long Score | Short Score |
|---|---|---|---|
| F1 Trend | EMA stack, Supertrend, ADX | Bullish alignment = 100 | Inverted |
| F2 Momentum | RSI position, MACD divergence, ROC z-score | Trend-conditional | Inverted |
| F3 Volume | Seasonal volume ratio, VWAP position, Volume z-score | Above VWAP + volume = 100 | Inverted |
| F4 Vol-Pos | ATR distance to support/resistance, BB position, ATR percentile | Near support = 100 | Near resistance = 100 |
| F5 Sector | RS-Ratio + RS-Momentum | Strong sector = 100 | Weak sector = 100 |
| F6 OI | OI buildup classification | Long buildup = 100 | Short buildup = 100 |
| F7 Pos-Rng | 52-week position, CPR distance, ORB position | Bottom 20% = 100 | Top 20% = 100 |

**Regime-Conditional Weights (sum = 100%):**
| Regime | F1 | F2 | F3 | F4 | F5 | F6 | F7 |
|---|---|---|---|---|---|---|---|
| Trending-Up | 25% | 20% | 12% | 5% | 18% | 12% | 8% |
| Trending-Down | 25% | 20% | 12% | 5% | 18% | 12% | 8% |
| Range-Bound | 8% | 5% | 18% | 30% | 15% | 12% | 12% |

**Scoring Algorithm:**
```python
S_raw = Σ(w_i × F_i)
S_liq = S_raw × liquidity_multiplier
S_final = S_liq + Σ(modifiers)
Score = clamp(S_final, 0, 100)

Short Score_effective = Short Score_raw × 0.92  # Asymmetry penalty
```

**Contextual Modifiers (additive):**
| Condition | Modifier |
|---|---|
| F&O Ban flag | -4 |
| Earnings during session | -6 |
| Stale data (>30 sec) | Score frozen |
| Strong sector tailwind | +3 |
| Weak sector headwind | -3 |
| Index constituent change (<5 days) | -2 |

### L6: Cross-Sectional Ranking Layer
**File:** `engine/layers/l6_ranking.py`

**Hysteresis (adaptive threshold):**
```python
σ_gap = std dev of score gaps between ranks 20-30
θ = max(2.0, 0.25 × σ_gap)

Entry: Rank 26+ enters Top 25 only if score > rank 25 by ≥ θ
Exit: Rank 25 drops out only if rank 26 exceeds it by ≥ θ

Target: ~1 rank change per minute
If rate > 1/min: θ += 10%
If rate < 0.5/min: θ -= 10%
```

**Rank Movement Tracking:**
- NEW: Entered within last 5 min
- UP: Improved 2+ positions in 5 min
- DOWN: Declined 2+ positions in 5 min
- STABLE: Unchanged (±1)

**Concentration Metrics (informational only):**
- Sector Concentration: Max count of single sector in Top 25 (>8 = theme day)
- Score Spread: Score(rank 1) - Score(rank 25) (>20 = strong conviction)
- Correlation Cluster: Pairs with cosine similarity > 0.70 (>15 = crowded)

### L7: Mechanical Confluence Layer
**File:** `engine/layers/l7_confluence.py`

**Six Deterministic Checks (boolean pass/fail):**

| # | Check | Pass Condition (Long) | Pass Condition (Short) |
|---|---|---|---|
| 1 | Strong Close | Close in upper 33% of H-L range | Close in lower 33% |
| 2 | Volume Confirmation | Seasonal vol ≥ 1.5× 20-bar median | Same |
| 3 | Non-Exhaustion | Bar range ≤ 1.5× 20-bar median | Same |
| 4 | Higher-TF Alignment | EMA(9)>EMA(20)>EMA(50) on 15-min | Inverse |
| 5 | Adequate Risk Distance | |Price - Invalidation| ≥ 0.5× ATR(14,5m) | Same |
| 6 | Adequate Reward Distance | |T1 - Price| ≥ 1.2× |Price - Invalidation| | Same |

**Time-of-Day Adjustments:**
- Opening Shock (9:15-9:30): Volume threshold raised to 2.0× (from 1.5×)

**Confluence Score:** 0-6 (count of passed checks)

### L8: Thesis Assembly Layer
**File:** `engine/layers/l8_thesis.py`

**Six Setup Types (all formally defined):**

| # | Setup | Trigger | Invalidation | T1 | T2 | Valid Window | Preferred Regime |
|---|---|---|---|---|---|---|---|
| 1 | ORB (15-min) | ORB High + 1 tick | max(ORB Low, VWAP-0.5%) | Trigger + 1.5× ORB Range | PDH | Until 11:00 AM | Trending-Up |
| 2 | VWAP Reclaim | VWAP cross above + volume | VWAP - 0.8× ATR | VWAP + 1.5× ATR | VWAP + 2.5× ATR | After 9:45 AM | Trending-Up |
| 3 | Supertrend Pullback | Pullback touches ST line from above | ST line - 0.5× ATR | ST line + 1.5× ATR | ST line + 2.5× ATR | Any (ST bullish) | Trending-Up |
| 4 | Mean Reversion | Price touches lower 2σ BB | Band breach below 2.5σ | VWAP (min 0.6× invalidation dist) | Opposite 1σ band | Any | Range-Bound |
| 5 | First Hour Breakout | Break above FH High after 10:15 | FH Low - 0.3× FH Range | Trigger + 1.0× FH Range | PDH | 10:15-12:00 PM | Trending-Up |
| 6 | CPR Breakout | Break above TC + volume | BC - 0.2× CPR Width | R1 Floor Pivot | R2 Floor Pivot | After 9:45 AM | Trending-Up |

*(Short setups are symmetric inverses)*

**Indian Cost Model:**
```
Equity Intraday (MIS):
  Brokerage: 0.03% or ₹20/order, whichever is lower (both sides)
  STT: 0.025% (sell only)
  Exchange: 0.00297% (both)
  SEBI: ₹10/crore = 0.0001% (both)
  Stamp: 0.003% (buy only)
  GST: 18% on (brokerage + exchange + SEBI) (both)

Futures Intraday:
  Brokerage: ₹20/leg flat
  STT: 0.0125% (sell)
  Exchange: 0.00173% (both)
  Stamp: 0.002% (buy)
  GST: 18% on (brokerage + exchange + SEBI)

Slippage (Depth-Derived):
  Excellent: 5 bps normal / +8 bps SL
  Good: 10 bps / +15 bps
  Marginal: 20 bps / +25 bps
  Poor: 35 bps / +40 bps
```

**Net R:R Computation:**
```python
Gross R:R = |T1 - Trigger| / |Trigger - Invalidation|
Round-trip cost % = Σ(charges) × 2 + slippage × 2
Net reward = |T1 - Trigger| - (cost% × Trigger)
Net risk = |Trigger - Invalidation| + (stop-slippage × Trigger)
Net R:R = Net reward / Net risk

Grade:
  ≥ 1.5: ATTRACTIVE (Green)
  1.0-1.5: MARGINAL (Amber)
  < 1.0: UNATTRACTIVE (Red)
```

**Time-Decay Function:**
```python
M(t) = exp(-λ × max(0, t - t_window)²)
λ = 0.0003 for ORB, 0.00015 for Supertrend/VWAP
```

| Time | ORB Multiplier | Supertrend/VWAP |
|---|---|---|
| 9:30-10:30 | 1.00 | 1.00 |
| 10:30-11:30 | 0.85 | 0.90 |
| 11:30-12:30 | 0.65 | 0.78 |
| 12:30-13:30 | 0.42 | 0.62 |
| 13:30-14:30 | 0.22 | 0.42 |
| After 14:30 | 0.08 | 0.22 |

**Actionability Tier:**
| Tier | Criteria | Visual |
|---|---|---|
| Tradeable | Clean path + Net R:R ≥ 1.0 + liquidity ≥ Good + no blocking flags | Full color, green badge |
| Constrained | Execution path exists but with friction (F&O ban workaround, marginal liquidity, cash-only MIS, Net R:R 0.8-1.0) | Yellow warning labels |
| Research-Only | No viable retail execution (cash-only short with no SLB, Net R:R < 0.8) | Greyed out, deprioritized |

### L9: Outcome Monitoring Layer
**File:** `engine/layers/l9_monitor.py`

**State Machine:**
```
CREATED → PENDING → TRIGGERED → ACTIVE → {T1_HIT, T2_HIT, STOPPED_OUT, INVALIDATED, EXPIRED}
                    ↓
              FORCE_EXPIRED at 15:15 IST
```

**Shadow Ledger (Phase 1 — no live orders):**
```python
# When trigger price is crossed in tick feed:
# 1. Record theoretical entry at trigger price
# 2. Track every subsequent tick for MFE/MAE
# 3. Monitor invalidation conditions every minute
# 4. If T1/T2 hit: record exit, compute gross/net return
# 5. If SL hit: record stop-out
# 6. If expiry time reached: FORCE_EXPIRED
```

**Per-Outcome Metrics:**
- Entry/Exit timestamps
- MFE / MAE (as % of entry)
- MFE/MAE timestamps
- Gross Return, Net Return (after costs)
- R-Multiple = Net Return / |Entry - Invalidation|
- Time-to-Trigger, Time-to-Exit

**Session Expiry Rules:**
| Setup | Pending Expiry | Force Expiry |
|---|---|---|
| ORB (15-min) | 11:00 AM | 15:15 IST |
| ORB (2-hour) | 13:00 PM | 15:15 IST |
| VWAP Reclaim | 14:00 PM | 15:15 IST |
| Supertrend Pullback | 14:30 PM | 15:15 IST |
| Mean Reversion | 13:30 PM | 15:15 IST |
| First Hour Breakout | 12:00 PM | 15:15 IST |
| CPR Breakout | 14:00 PM | 15:15 IST |

**Conditional Extension:** If VIX recovering from lunch lows + 5-min realized vol > 80th percentile of session → extend VWAP/Supertrend expiry by 30 min.

### L10: Hierarchical Edge Lookup Layer
**File:** `engine/layers/l10_edge.py`

**Six-Tier Fallback Structure:**

| Tier | Aggregation | Approx. Cells | Quality Gate | Timeline |
|---|---|---|---|---|
| 1 | Setup × Regime × Sector × Time-bucket | 2,772 (L/S separate) | n ≥ 30, CI ≤ 15% | Year 2+ |
| 2 | Setup × Regime × Time-bucket | 126 | n ≥ 40, CI ≤ 14% | Month 6+ |
| 3 | Setup × Regime | 18 | n ≥ 50, CI ≤ 14% | Month 3+ |
| 4 | Setup × Time-bucket | 42 | n ≥ 50, CI ≤ 14% | Month 2+ |
| 5 | Setup baseline | 6 | n ≥ 80, CI ≤ 12% | Month 1+ |
| 6 | Global baseline | 1 | n ≥ 50, CI ≤ 14% | Week 1+ |

**Wilson Confidence Interval:**
```python
# For binomial proportion p̂ = k/n
# CI half-width at p̂=0.5:
# n=30: 17.8%, n=40: 15.4%, n=50: 13.9%, n=80: 11.0%, n=100: 9.8%, n=150: 8.0%
```

**Benjamini-Hochberg FDR Control:**
```python
# Step 1: Compute p-values for all cells at tier (H0: hit rate = 50%)
# Step 2: Order p-values
# Step 3: Find largest k where p(k) ≤ (k/m) × 0.10
# Step 4: Cells 1..k flagged as significant edge
# Step 5: Failing cells display "tentative" indicator
```

**Bayesian Bootstrap Fallback (early weeks):**
```python
# Prior: Beta(α=12, β=8) centered at 60% hit rate
# Posterior: Beta(α + k, β + n - k)
# Display: "Bootstrap Edge (literature prior + n=[observed])"
```

**Tier Promotion Tracking:**
- Dashboard "Edge Maturation" panel
- Weekly email summary of tier promotions

---

## 6. Database Schema (TimescaleDB)

### Hypertable: `market_bars`
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

### Hypertable: `thesis_outcomes`
```sql
CREATE TABLE thesis_outcomes (
    time TIMESTAMPTZ NOT NULL,
    thesis_id UUID,
    symbol TEXT,
    direction TEXT, -- LONG or SHORT
    setup_type INT, -- 1-6
    regime INT, -- 1-3
    sector INT, -- 1-11
    time_bucket INT, -- 1-7
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

### Continuous Aggregate: `edge_stats_daily`
```sql
CREATE MATERIALIZED VIEW edge_stats_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) as day,
    setup_type,
    regime,
    sector,
    time_bucket,
    direction,
    COUNT(*) as n,
    AVG(hit::int) as hit_rate,
    AVG(net_return_pct) as avg_net_return,
    STDDEV(net_return_pct) as std_net_return
FROM thesis_outcomes
GROUP BY 1, 2, 3, 4, 5, 6;
```

### Static Tables:
- `instruments` — symbol, instrument_key, segment, isin, lot_size, tick_size
- `nse_flags` — symbol, date, fo_ban, mwpl_status, earnings_flag, circuit_limit
- `volume_seasonality` — symbol, time_bucket, avg_volume_10d, std_volume_10d
- `session_calendar` — date, is_trading_day, is_expiry, event_flag

---

## 7. Redis Key Structure

```
market:context → JSON (L1 Market Context Frame)
market:global_cues → JSON (SGX, Dow, Brent, USDINR from 6 AM)

universe:{symbol} → Hash (L2 flags: fo_eligible, fo_ban, mwpl, earnings, lqs, shortability)
universe:ban_list → Set (symbols currently in F&O ban)
universe:earnings_today → Set (symbols with earnings today)

bars:latest:{instrument_key} → Hash (last 1-min OHLCV + OI)
bars:session:{instrument_key} → Sorted Set (all ticks for VWAP computation)

top25:long → Sorted Set (score → symbol)
top25:short → Sorted Set (score → symbol)
top25:movement:{symbol} → String (NEW/UP/DOWN/STABLE)

thesis:{thesis_id} → Hash (full thesis card)
thesis:active → Set (IDs of active theses)
thesis:invalidation:{thesis_id} → Hash (current invalidation conditions)

l10:tier:{tier_num}:{setup}:{regime}:{sector}:{time_bucket}:{direction} → Hash (n, hit_rate, ci_lower, ci_upper, is_significant)
```

---

## 8. API Design (FastAPI)

### REST Endpoints

```
GET  /health                          → Engine health + token status
GET  /market/context                  → Current L1 Market Context Frame
GET  /rankings/top25/long            → Current Top 25 Long (with movement)
GET  /rankings/top25/short           → Current Top 25 Short (with movement)
GET  /thesis/{thesis_id}             → Full thesis card (L8 lazy path)
GET  /thesis/{thesis_id}/outcome     → L9 outcome metrics (if terminal)
GET  /edge/tiers                     → L10 active tiers + promotion events
GET  /edge/tier/{tier_id}/stats      → Specific tier statistics
POST /admin/refresh-token            → Manual token refresh trigger
```

### WebSocket Endpoint

```
WS /ws/v1/stream

Client → Server: {"action": "subscribe", "channels": ["market", "rankings", "theses"]}
Server → Client:
  {"type": "L1_CONTEXT", "timestamp": "...", "payload": {...}}
  {"type": "L6_RANKINGS", "timestamp": "...", "payload": {"long": [...], "short": [...]}}
  {"type": "L8_THESIS", "timestamp": "...", "payload": {"thesis_id": "...", "card": {...}}}
  {"type": "L9_INVALIDATION", "timestamp": "...", "payload": {"thesis_id": "...", "reason": "..."}}
  {"type": "L10_EDGE", "timestamp": "...", "payload": {"tier": 2, "promotion": "..."}}
```

---

## 9. Frontend Design (React PWA)

### Dashboard Layout
```
┌─────────────────────────────────────────────────────────────┐
│  REGIME: Trending-Up (Volatile)  VIX: 23.4  BREADTH: Strong │  ← L1 Banner
├──────────────────────────┬──────────────────────────────────┤
│  TOP 25 LONG             │  TOP 25 SHORT                    │
│  [RELIANCE ↑]  Score: 84 │  [TATAMOTORS ↓]  Score: 87      │
│  Setup: ORB | Conf: 5/6  │  Setup: VWAP | Conf: 6/6        │
│  Net R:R: 1.4 [ATTRACTIVE]│  Net R:R: 1.1 [MARGINAL]       │
├──────────────────────────┴──────────────────────────────────┤
│  ACTIVE THESIS MONITOR (L9)                                 │
│  [SBIN] TRIGGERED → T1_HIT (+0.92%) @ 10:45 AM              │
│  [INFY] PENDING → Invalidated (Price below VWAP)          │
├─────────────────────────────────────────────────────────────┤
│  EDGE MATURATION PANEL (L10)                                │
│  Tier 2 promoted: ORB×Trending-Up×10:30 now has n=42       │
│  Tier 3 approaching: Supertrend×Range-Bound (n=38)          │
└─────────────────────────────────────────────────────────────┘
```

### PWA Features
- **Installable:** Add to home screen on mobile
- **Background Sync:** Queue thesis expands when offline
- **Push Notifications:** Critical invalidation alerts (via Web Push API)
- **Offline Cache:** Static assets + last known rankings

---

## 10. Deployment (Docker Compose)

```yaml
version: '3.8'

services:
  engine:
    build:
      context: ./engine
      dockerfile: Dockerfile
    container_name: intraday-engine
    restart: unless-stopped
    env_file: .env
    ports:
      - "8000:8000"
    volumes:
      - engine_data:/data          # Persistent token storage
      - ./logs:/app/logs
      - ./engine:/app              # Dev mount (remove in prod)
    depends_on:
      - timescaledb
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  timescaledb:
    image: timescale/timescaledb:latest-pg15
    container_name: intraday-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: engine
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: intraday
    volumes:
      - tsdb_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    container_name: intraday-cache
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  web:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: intraday-web
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - engine

volumes:
  engine_data:
  tsdb_data:
  redis_data:
  caddy_data:
  caddy_config:
```

### Environment File (.env)
```bash
# Upstox (Phase 1: Research Only — Analytics Token is sufficient)
UPSTOX_ANALYTICS_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
UPSTOX_API_KEY=your_api_key              # Phase 2 only
UPSTOX_API_SECRET=your_secret            # Phase 2 only
UPSTOX_REDIRECT_URL=https://your-vps.com/callback

# Database
DB_PASSWORD=your_secure_password
DATABASE_URL=postgresql+asyncpg://engine:${DB_PASSWORD}@timescaledb:5432/intraday

# Cache
REDIS_URL=redis://redis:6379/0

# Alerts
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

---

## 11. Scheduling & Automation

### APScheduler Job Registry

| Job ID | Trigger | Function | Description |
|---|---|---|---|
| `pre_market_globals` | Cron 6:00 AM | `fetch_global_cues()` | GIFT, Dow, Brent, USDINR |
| `nse_scraper` | Cron 8:00 AM | `refresh_universe_flags()` | Ban, MWPL, earnings, instrument master |
| `ws_connect` | Cron 9:14 AM | `connect_market_data()` | Connect Upstox WS |
| `reference_levels` | Cron 9:15 AM | `compute_reference_levels()` | CPR, pivots, ORB, FH |
| `minute_bar` | Cron *:*:05 | `process_minute_bar()` | L3-L8 full pipeline |
| `regime_recheck` | Cron */5:00 | `recheck_regime()` | L1 regime + weight update |
| `oi_refresh` | Cron */15:00 | `refresh_oi_signals()` | L3 OI + options signals |
| `conditional_extension` | Cron 13:30 | `check_extension()` | Extend VWAP/Supertrend expiry |
| `force_expire` | Cron 15:15 | `force_expire_all()` | Expire all pending |
| `ws_disconnect` | Cron 15:30 | `disconnect_market_data()` | Clean WS close |
| `token_refresh` | Cron 3:35 AM | `refresh_access_token()` | OAuth auto-refresh (Phase 2) |
| `l10_rebuild` | Cron 23:00 | `nightly_rebuild()` | Edge stats + seasonality |

### Holiday Handling
```python
# Every job checks is_trading_day() before executing
# If holiday: log "NSE Holiday. Engine sleeping.", skip market jobs
# Non-market jobs (token_refresh, l10_rebuild) run regardless
```

---

## 12. Token Management

### Analytics Token (Phase 1 — Primary)
- **Valid for 1 year**
- **No refresh needed**
- **No daily login**
- **Used for:** Historical data, WebSocket, quotes, option chain, charges preview

### OAuth Token (Phase 2 — Optional, for Live Execution)
- **Access token:** Expires 3:30 AM IST daily
- **Refresh token:** Long-lived (months)
- **Auto-refresh:** Scheduled job at 3:35 AM calls `POST /v2/login/authorization/token` with `grant_type=refresh_token`
- **Failure mode:** If refresh fails, engine halts, sends Telegram alert, waits for manual `/auth/setup`

### One-Time Setup (OAuth — Only if adding execution later)
1. Deploy engine
2. Visit `https://your-vps.com/auth/setup`
3. Redirects to Upstox login → authorize
4. Redirects back with `code`
5. Engine exchanges `code` for `access_token + refresh_token`
6. Stores `refresh_token` to `/data/upstox_tokens.json` (persistent volume)
7. **Never needs browser again** (until refresh token dies)

---

## 13. Monitoring & Alerting

### Telegram Alert Types

| Severity | Event | Message |
|---|---|---|
| INFO | Engine start | 🟢 Intraday Engine started. Market open in X hours. |
| INFO | WS connected | ✅ Market data live. 120 instruments subscribed. |
| INFO | Regime change | 📊 Regime: Range-Bound → Trending-Up (Volatile) |
| INFO | New thesis | 🔔 RELIANCE entered Top 25 Short (Score: 84, ORB) |
| INFO | Thesis triggered | 🎯 TATAMOTORS LONG triggered @ ₹715.00 |
| INFO | Thesis exit | ✅ TATAMOTORS T1_HIT (+0.98%) @ 10:45 AM |
| WARN | Invalidation | ⚠️ INFY invalidated (Price below VWAP) |
| WARN | WS drop | ⚠️ WS dropped. Reconnecting in 4s... (attempt 2/5) |
| WARN | Low conviction | ⚠️ Score spread < 10. Market uncertain. |
| CRITICAL | WS dead | 🚨 CRITICAL: WS dead after 5 retries. |
| CRITICAL | Token expired | 🚨 CRITICAL: Refresh token expired. Re-run /auth/setup |
| DAILY | EOD summary | 📈 EOD: 12 triggered, 8 T1, 2 SL, 2 expired. Tier 2 promoted. |
| DAILY | Holiday | 😴 NSE Holiday. Engine sleeping. |

### Health Endpoint
```json
GET /health
{
  "status": "healthy",
  "websocket": "connected",
  "last_bar_processed": "2026-05-16T10:30:05+05:30",
  "top25_long_count": 25,
  "top25_short_count": 25,
  "active_theses": 4,
  "token_expires_in_days": 287,
  "db_connected": true,
  "redis_connected": true,
  "scheduler_jobs": 12
}
```

---

## 14. Development Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [ ] Docker Compose setup (Engine + TimescaleDB + Redis)
- [ ] Upstox REST client (historical data, option chain, charges)
- [ ] Upstox WebSocket client (connect, reconnect, protobuf parsing)
- [ ] NSE scraper (F&O ban, MWPL, earnings)
- [ ] L1 Market Context (regime, VIX, breadth)
- [ ] L2 Universe Enrichment (flags, LQS)

### Phase 2: Signal Engine (Weeks 3-4)
- [ ] L3 Per-Stock Signals (all indicators)
- [ ] L4 Sector Context (RS-Ratio, RS-Momentum)
- [ ] L5 Multi-Factor Scoring (Polars implementation)
- [ ] L6 Cross-Sectional Ranking (hysteresis, movement tracking)
- [ ] L7 Mechanical Confluence (6 checks)

### Phase 3: Thesis & Dashboard (Weeks 5-6)
- [ ] L8 Thesis Assembly (all 6 setups, cost model, time-decay)
- [ ] React PWA scaffold (Vite + Tailwind + Zustand)
- [ ] Dashboard layout (L1 banner, Top 25 tables, thesis cards)
- [ ] WebSocket integration (live updates)

### Phase 4: Outcome Tracking (Week 7)
- [ ] L9 Shadow Ledger (state machine, MFE/MAE)
- [ ] Invalidation monitors (per-minute checks)
- [ ] Session expiry logic (setup-type dependent)

### Phase 5: Edge Statistics (Weeks 8-9)
- [ ] L10 Hierarchical Edge Lookup (6 tiers)
- [ ] Wilson CI computation
- [ ] Benjamini-Hochberg FDR control
- [ ] Bayesian Bootstrap fallback
- [ ] Tier promotion tracking

### Phase 6: Polish & Hardening (Week 10)
- [ ] Telegram alerting integration
- [ ] Health checks + monitoring
- [ ] NSE holiday handling
- [ ] Error recovery + circuit breakers
- [ ] Performance optimization (Polars tuning)

### Phase 7: Execution (Future — Optional)
- [ ] OAuth token management
- [ ] OpenAlgo integration (or direct Upstox orders)
- [ ] Paper trading validation
- [ ] Live execution (manual approval → full auto)

---

## 15. File Structure

```
intraday-engine/
├── docker-compose.yml
├── .env
├── README.md
│
├── engine/                          # FastAPI Backend
│   ├── Dockerfile
│   ├── main.py                      # FastAPI app + lifespan
│   ├── config.py                    # Pydantic Settings
│   │
│   ├── core/
│   │   ├── auth/
│   │   │   ├── token_manager.py     # Analytics + OAuth auto-refresh
│   │   │   └── oauth_routes.py      # /auth/setup callback
│   │   ├── data/
│   │   │   ├── upstox_rest.py       # REST client (httpx)
│   │   │   ├── upstox_ws.py         # WebSocket client (protobuf)
│   │   │   ├── nse_scraper.py       # Ban/MWPL/earnings scraper
│   │   │   └── redis_cache.py       # Redis helper
│   │   ├── scheduler/
│   │   │   └── market_scheduler.py  # APScheduler registry
│   │   └── alerts/
│   │       └── telegram.py          # Telegram bot alerts
│   │
│   ├── layers/
│   │   ├── l1_market_context.py
│   │   ├── l2_universe.py
│   │   ├── l3_signals.py
│   │   ├── l4_sector.py
│   │   ├── l5_scoring.py
│   │   ├── l6_ranking.py
│   │   ├── l7_confluence.py
│   │   ├── l8_thesis.py
│   │   ├── l9_monitor.py
│   │   └── l10_edge.py
│   │
│   ├── models/
│   │   ├── frames.py                # Pydantic: MarketContext, Thesis, etc.
│   │   └── enums.py                 # Regime, SetupType, Tier, etc.
│   │
│   ├── api/
│   │   ├── rest_routes.py           # /health, /market, /rankings, /thesis, /edge
│   │   └── websocket_manager.py     # WS broadcast to React clients
│   │
│   └── db/
│       ├── timescale.py             # Asyncpg connection + hypertable setup
│       └── migrations/
│           ├── 001_initial.sql
│           └── 002_continuous_aggs.sql
│
├── frontend/                        # React PWA
│   ├── Dockerfile
│   ├── vite.config.ts
│   ├── index.html
│   ├── public/
│   │   └── manifest.json
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── RegimeBanner.tsx
│   │   │   ├── Top25Table.tsx
│   │   │   ├── ThesisCard.tsx
│   │   │   ├── ActiveMonitor.tsx
│   │   │   └── EdgePanel.tsx
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts
│   │   │   ├── useMarketContext.ts
│   │   │   └── useRankings.ts
│   │   ├── stores/
│   │   │   └── marketStore.ts       # Zustand
│   │   ├── types/
│   │   │   └── api.ts               # TypeScript interfaces
│   │   └── lib/
│   │       └── utils.ts
│   └── package.json
│
└── scripts/
    ├── deploy.sh
    └── backup.sh
```

---

## 16. Key Decisions & Rationale

| Decision | Rationale |
|---|---|
| **Pure Upstox, no OpenAlgo (Phase 1)** | OpenAlgo does not proxy Analytics APIs (OI, PCR, Max Pain, historical bars with OI). Adding it creates dual auth + latency for zero data benefit. Add OpenAlgo only when executing live orders. |
| **Analytics Token primary** | 1-year validity, zero daily login, covers all data needs for research. OAuth only needed for order placement. |
| **Shadow Ledger for L9** | Upstox has no paper trading API. Internal simulation tracks MFE/MAE precisely per v1.2 spec without external dependencies. |
| **TimescaleDB over SQLite** | L10 requires millions of rows, continuous aggregates, and time-bucketing. SQLite would choke. TimescaleDB is built for this. |
| **Polars over Pandas** | 10-50x faster for 100-row × 7-factor cross-sectional scoring. Lazy evaluation ideal for L5-L6. |
| **2 WebSocket connections** | Upstox limit: 50 instruments/conn in Full mode. Split: 100 stocks (Full) + indices (LTPC) = 120 total. |
| **Mumbai VPS** | <5ms latency to NSE. Critical for tick data integrity. |
| **Telegram over email** | Instant, reliable, mobile-native. Traders need alerts on their phone. |

---

## 17. Risk Register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Upstox API rate limit hit | Low | Data gaps | Exponential backoff, request batching, priority queue |
| WebSocket disconnect mid-session | Medium | 2-60s data gap | Auto-reconnect with 5 retries, alert after failure |
| Analytics Token expires (1 year) | Low | Complete data stop | Alert 7 days before expiry, manual renewal |
| NSE scraper fails (8 AM) | Low | Stale ban/earnings data | Retry 3x, alert if still failing, use yesterday's data |
| VPS crash/reboot | Low | Engine stops | Docker `restart: unless-stopped`, health checks |
| Polars computation > 1 min | Very Low | Missed bar close | Performance monitoring, optimize with lazy frames |
| Refresh token invalidated (Phase 2) | Very Low | Order placement stops | Alert + manual re-auth at `/auth/setup` |

---

**END OF DOCUMENT**

*This specification is locked. Implementation begins with Phase 1: Foundation.*
