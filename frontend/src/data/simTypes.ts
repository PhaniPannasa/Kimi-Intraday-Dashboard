// Synthetic Nifty 100 data generator — deterministic, controllable live drift.
// Models the full L1→L10 pipeline shapes matching the engine output.
// Used for rich UI rendering; real API hooks take over when backend data arrives.

export const SETUP_TYPES: Record<number, string> = {
  1: 'ORB-15m', 2: 'VWAP Reclaim', 3: 'ST Pullback',
  4: 'Mean Reversion', 5: '1H Breakout', 6: 'CPR Breakout',
};

export const SECTORS: { id: number; name: string }[] = [
  { id: 1, name: 'Financials' }, { id: 2, name: 'IT' }, { id: 3, name: 'Auto' },
  { id: 4, name: 'FMCG' }, { id: 5, name: 'Pharma' }, { id: 6, name: 'Metals' },
  { id: 7, name: 'Energy' }, { id: 8, name: 'Telecom' }, { id: 9, name: 'Realty' },
  { id: 10, name: 'Cement' }, { id: 11, name: 'Power' },
];



export interface SimStock {
  symbol: string;
  instrument_key: string;
  sector_id: number;
  sector_name: string;
  direction: 'LONG' | 'SHORT';
  price: number;
  change_pct: number;
  spark: number[];
  // L2
  fo_eligible: boolean;
  fo_ban: boolean;
  mwpl_status: string;
  earnings_flag: string;
  lqs: number;
  liquidity_quality: string;
  // L3
  ema_9: number;
  ema_20: number;
  ema_50: number;
  ema_aligned: boolean;
  supertrend_dir: number;
  adx: number;
  rsi: number;
  macd_hist: number;
  atr: number;
  atr_pct: number;
  bb_width: number;
  vwap: number;
  above_vwap: boolean;
  roc_20: number;
  // L4
  rs_ratio: number;
  rs_momentum: number;
  sector_rank: number;
  // L5
  f1_trend: number;
  f2_momentum: number;
  f3_volume: number;
  f4_volpos: number;
  f5_structure: number;
  f6_sector: number;
  f7_risk: number;
  score: number;
  // L6
  prev_score: number;
  score_change: number;
  rank_movement: 'NEW' | 'UP' | 'DOWN' | 'STABLE';
  // L7
  checks: Record<string, boolean>;
  confluence_score: number;
  // L8
  setup_type: number;
  setup_label: string;
  trigger: number;
  invalidation: number;
  t1: number;
  t2: number;
  gross_rr: number;
  net_rr: number;
  grade: string;
  tier: string;
  time_decay: number;
  valid_until_min: number;
  thesis_id: string;
  // Candle data
  candles: { o: number; h: number; l: number; c: number }[];
  // L9
  state: string;
  mfe_R: number;
  mae_R: number;
  // L10
  edge_tier: number;
}

export interface SimMarketContext {
  regime: string;
  regime_confidence: number;
  volatility_qualifier: string;
  vix_band: string;
  vix_value: number;
  vix_trajectory: string;
  breadth: string;
  premarket_bias: string;
  time_bucket: string;
  event_flag: string | null;
  bank_nifty_divergence: number;
}

export interface SimPipelineLayer {
  key: string;
  label: string;
  name: string;
  status: string;
  duration_ms: number;
  last_run: number;
}

export interface SimUniverse {
  longs: SimStock[];
  shorts: SimStock[];
  cycle: number;
}

export interface SimSnapshot {
  universe: SimUniverse;
  ctx: SimMarketContext;
  pipeline: SimPipelineLayer[];
}

export const LAYER_META: Record<string, { name: string; purpose: string }> = {
  L1: { name: 'Market Context', purpose: 'Market regime, VIX band, breadth, and time-bucket context' },
  L2: { name: 'Universe', purpose: 'Universe eligibility — F&O ban, MWPL, earnings, liquidity quality' },
  L3: { name: 'Signals', purpose: 'Per-stock indicators — EMA alignment, ADX, RSI, MACD, ATR, BB, VWAP' },
  L4: { name: 'Sector', purpose: 'Sector relative strength and rotation rank' },
  L5: { name: 'Scoring', purpose: 'Multi-factor composite score (7 factors × regime weights)' },
  L6: { name: 'Ranking', purpose: 'Cross-sectional ranking with hysteresis tracking' },
  L7: { name: 'Confluence', purpose: 'Mechanical confluence pass/fail checks (6 gates)' },
  L8: { name: 'Thesis', purpose: 'Thesis assembly — entry, invalidation, T1, T2, cost model, time decay' },
  L9: { name: 'Monitor', purpose: 'Shadow ledger — MFE/MAE/R-multiple tracking per thesis' },
  L10: { name: 'Edge', purpose: 'Edge statistics — Wilson CI, BH FDR, Bayesian bootstrap per tier' },
};

// ── Fabricator functions (genStock, genUniverse, genMarketContext, genPipelineStatus,
//     computeFunnel) removed — Phase A truthful-data-source: no client-side PRNG data.
//     Only the evaluateLayers utility and shared types remain.

// Evaluate a stock through all layers for the Journey view
export function evaluateLayers(entry: SimStock, ctx: SimMarketContext) {
 {
  const isLong = entry.direction === 'LONG';
  const dirAligned =
    (isLong && ctx.regime === 'Trending-Up') ||
    (!isLong && ctx.regime === 'Trending-Down') ||
    ctx.regime === 'Range-Bound';

  return {
    L1: {
      verdict: dirAligned ? 'PASS' : 'WARN',
      headline: `${ctx.regime} · VIX ${ctx.vix_value.toFixed(1)} ${ctx.vix_band}`,
      reason: dirAligned ? `Regime supports ${entry.direction.toLowerCase()} setups` : `${entry.direction} bias fighting ${ctx.regime} regime`,
      chips: [{ label: ctx.regime, kind: ctx.regime === 'Trending-Up' ? 'long' : ctx.regime === 'Trending-Down' ? 'short' : 'neutral' }],
    },
    L2: {
      verdict: entry.fo_ban ? 'FAIL' : (entry.lqs < 0.7 || entry.earnings_flag !== 'None') ? 'WARN' : 'PASS',
      headline: `LQS ${(entry.lqs * 100).toFixed(0)} (${entry.liquidity_quality})`,
      reason: entry.fo_ban ? 'BANNED — F&O ban-list' : 'Passed liquidity & eligibility gates',
    },
    L3: {
      verdict: entry.ema_aligned ? 'PASS' : 'WARN',
      headline: `EMA ${entry.ema_aligned ? 'aligned' : 'mixed'} · RSI ${entry.rsi.toFixed(0)} · ADX ${entry.adx.toFixed(0)}`,
      reason: entry.ema_aligned ? `Full ${isLong ? 'bullish' : 'bearish'} signal stack` : 'Signals mixed',
      factors: [
        { label: 'Trend', v: entry.f1_trend },
        { label: 'Momentum', v: entry.f2_momentum },
        { label: 'Volume', v: entry.f3_volume },
        { label: 'Vol-Pos', v: entry.f4_volpos },
        { label: 'Structure', v: entry.f5_structure },
        { label: 'Sector', v: entry.f6_sector },
        { label: 'Risk', v: entry.f7_risk },
      ],
    },
    L4: {
      verdict: (entry.rs_ratio > 1.02 && entry.rs_momentum > 1) ? 'PASS' : entry.rs_ratio < 0.98 ? 'FAIL' : 'WARN',
      headline: `${entry.sector_name} #${entry.sector_rank} · RS-Ratio ${entry.rs_ratio.toFixed(3)}`,
      reason: entry.rs_ratio > 1.02 ? `${entry.sector_name} outperforming` : `${entry.sector_name} in line`,
    },
    L5: {
      verdict: entry.score >= 75 ? 'PASS' : entry.score >= 60 ? 'WARN' : 'FAIL',
      headline: `Composite ${entry.score.toFixed(1)}`,
      reason: entry.score >= 75 ? 'Multi-factor confirmation' : 'Mid-tier score',
    },
    L6: {
      verdict: entry.rank_movement === 'UP' || entry.rank_movement === 'NEW' ? 'PASS' : entry.rank_movement === 'DOWN' ? 'WARN' : 'PASS',
      headline: `Δ ${entry.score_change >= 0 ? '+' : ''}${entry.score_change.toFixed(2)} · ${entry.rank_movement}`,
      reason: entry.rank_movement === 'NEW' ? 'New entrant this cycle' : entry.rank_movement === 'UP' ? 'Rising in rank' : 'Steady',
    },
    L7: {
      verdict: entry.confluence_score >= 5 ? 'PASS' : entry.confluence_score >= 3 ? 'WARN' : 'FAIL',
      headline: `${entry.confluence_score}/6 confluence checks passed`,
      reason: entry.confluence_score >= 5 ? 'High-quality confluence' : 'Partial confluence',
      checkRows: Object.entries(entry.checks).map(([label, ok]) => ({ label: label.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()), ok })),
    },
    L8: {
      verdict: entry.grade === 'ATTRACTIVE' ? 'PASS' : entry.grade === 'MARGINAL' ? 'WARN' : 'FAIL',
      headline: `${entry.setup_label} · Net R:R ${entry.net_rr.toFixed(2)}`,
      reason: entry.grade === 'ATTRACTIVE' ? 'Thesis published as Tradeable' : 'R:R below threshold',
      levels: { trigger: entry.trigger, invalidation: entry.invalidation, t1: entry.t1, t2: entry.t2, gross_rr: entry.gross_rr, net_rr: entry.net_rr, decay: entry.time_decay, tier: entry.tier, grade: entry.grade, setup: entry.setup_label },
    },
    L9: {
      verdict: entry.state === 'PENDING' ? 'NA' : entry.state === 'ACTIVE' || entry.state === 'T1_HIT' || entry.state === 'TRIGGERED' ? 'LIVE' : 'WARN',
      headline: `State ${entry.state} · MFE +${entry.mfe_R.toFixed(2)}R`,
      reason: entry.state === 'PENDING' ? `Waiting for trigger at ${entry.trigger.toFixed(2)}` : 'Live in shadow ledger',
      state: entry.state,
    },
    L10: {
      verdict: entry.edge_tier <= 2 ? 'PASS' : entry.edge_tier <= 4 ? 'WARN' : 'NA',
      headline: `T${entry.edge_tier} · hit rate ${((0.42 + (7 - entry.edge_tier) * 0.05) * 100).toFixed(0)}%`,
      reason: entry.edge_tier <= 2 ? 'Promoted tier — historical edge confirmed' : 'Mid tier — smaller size',
      edge: { tier: entry.edge_tier, hit: 0.42 + (7 - entry.edge_tier) * 0.05, ci_lo: 0.32 + (7 - entry.edge_tier) * 0.04, ci_hi: 0.55 + (7 - entry.edge_tier) * 0.05, n: 20 + (7 - entry.edge_tier) * 18, setup: entry.setup_label, regime: ctx.regime },
    },
  };
}
}
