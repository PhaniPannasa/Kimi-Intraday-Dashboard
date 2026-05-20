export type Regime = 'Trending-Up' | 'Trending-Down' | 'Range-Bound';
export type Direction = 'LONG' | 'SHORT';
export type RankMovement = 'NEW' | 'UP' | 'DOWN' | 'STABLE';
export type ActionabilityTier = 'Tradeable' | 'Constrained' | 'Research-Only';
export type ThesisState = 'CREATED' | 'PENDING' | 'TRIGGERED' | 'ACTIVE' | 'T1_HIT' | 'T2_HIT' | 'STOPPED_OUT' | 'INVALIDATED' | 'EXPIRED' | 'FORCE_EXPIRED';
export type VIXBand = 'Compressed' | 'Normal' | 'Elevated';
export type Breadth = 'Strong' | 'Mixed' | 'Weak';
export type LiquidityQuality = 'Excellent' | 'Good' | 'Marginal' | 'Poor';

export const setupTypeLabels: Record<number, string> = {
  1: 'ORB 15Min',
  2: 'VWAP Reclaim',
  3: 'ST Pullback',
  4: 'Mean Reversion',
  5: '1H Breakout',
  6: 'CPR Breakout',
};

export interface MarketContextFrame {
  regime: Regime;
  regime_confidence: number;
  volatility_qualifier: string;
  vix_band: VIXBand;
  vix_trajectory: string;
  vix_value: number;
  time_bucket: string;
  event_flag: string | null;
  breadth: Breadth;
  premarket_bias: string;
  bank_nifty_divergence: number;
}

export interface RankingEntry {
  symbol: string;
  instrument_key: string;
  direction: Direction;
  score: number;
  setup_type: number;
  setup_label?: string;
  confluence_score: number;
  net_rr: number;
  actionability_tier: ActionabilityTier;
  rank_movement: RankMovement;
  liquidity_quality: LiquidityQuality;
  // Rich fields
  price?: number;
  change_pct?: number;
  sector_name?: string;
  sector_id?: number;
  rs_ratio?: number;
  rs_momentum?: number;
  sparkline?: number[];
  state?: string;
  edge_tier?: number;
}

export interface ThesisCard {
  thesis_id: string;
  symbol: string;
  direction: Direction;
  setup_type: number;
  trigger: number;
  invalidation: number;
  t1: number;
  t2: number;
  gross_rr: number;
  net_rr: number;
  grade: string;
  confluence_score: number;
  time_decay_multiplier: number;
  actionability_tier: ActionabilityTier;
  valid_until: string;
  preferred_regime: Regime;
}

export interface ThesisOutcome {
  thesis_id: string;
  state: ThesisState;
  entry_ts: string | null;
  exit_ts: string | null;
  entry_price: number | null;
  exit_price: number | null;
  mfe_pct: number;
  mae_pct: number;
  gross_return_pct: number;
  net_return_pct: number;
  r_multiple: number;
  time_to_trigger_min: number | null;
  time_to_exit_min: number | null;
}

export interface EdgeTierStats {
  tier_id: number;
  setup_type: number;
  regime: Regime;
  sector: number | null;
  time_bucket: number | null;
  direction: Direction;
  n: number;
  hit_rate: number;
  ci_lower: number;
  ci_upper: number;
  is_significant: boolean;
  avg_net_return: number;
  std_net_return: number;
}

export interface L2UniverseFrame {
  fo_eligible: boolean;
  fo_ban: boolean;
  mwpl_status: string;
  earnings_flag: string;
  liquidity_quality: string;
  lqs_score: number;
}

export interface L3SignalFrame {
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
}

export interface L4SectorFrame {
  sector_id: number;
  sector_name: string;
  rs_ratio: number;
  rs_momentum: number;
  rotation_rank: number;
}

export interface L5ScoreBreakdown {
  total: number;
  f1_trend: number;
  f2_momentum: number;
  f3_volume: number;
  f4_volpos: number;
  f5_structure: number;
  f6_sector: number;
  f7_risk: number;
  regime: Regime;
  modifiers: Record<string, number>;
}

export interface L6RankSnapshot {
  previous_score: number;
  score_change: number;
  rank_movement: RankMovement;
  liquidity_quality: string;
}

export interface L7ConfluenceCheck {
  score: number;
  max: number;
  checks: Record<string, boolean>;
}

export interface L8ThesisSnapshot {
  thesis_id: string;
  setup_type: number;
  trigger: number;
  invalidation: number;
  t1: number;
  t2: number;
  gross_rr: number;
  net_rr: number;
  grade: string;
  actionability_tier: ActionabilityTier;
}

export interface SymbolFactorBreakdown {
  symbol: string;
  direction: Direction;
  last_updated: string;
  l2_universe: L2UniverseFrame;
  l3_signals: L3SignalFrame;
  l4_sector: L4SectorFrame;
  l5_scores: L5ScoreBreakdown;
  l6_ranking: L6RankSnapshot;
  l7_confluence: L7ConfluenceCheck;
  l8_thesis: L8ThesisSnapshot;
  l9_monitor?: L9MonitorSnapshot;
  l10_edge?: L10EdgeSnapshot;
  price?: number;
  change_pct?: number;
  sparkline?: number[];
}

export interface L9MonitorSnapshot {
  state: string;
  mfe_R: number;
  mae_R: number;
  entry_price?: number | null;
  current_price?: number | null;
}

export interface L10EdgeSnapshot {
  edge_tier: number;
  hit_rate: number;
  ci_lower: number;
  ci_upper: number;
  n_samples: number;
  is_significant: boolean;
}

export interface PipelineLayerStatus {
  status: string;
  last_run: string | null;
  duration_ms: number;
}

export interface PipelineStatusResponse {
  last_cycle_at: string | null;
  cycle_number: number;
  cycle_duration_ms: number;
  market_session: string;
  time_bucket: string;
  layers: Record<string, PipelineLayerStatus>;
  funnel_counts?: Record<string, { in: number; out: number }> | null;
}

// ── Constants imported from simTypes (shared across components) ──

export const SECTORS: { id: number; name: string }[] = [
  { id: 1, name: 'Financials' }, { id: 2, name: 'IT' }, { id: 3, name: 'Auto' },
  { id: 4, name: 'FMCG' }, { id: 5, name: 'Pharma' }, { id: 6, name: 'Metals' },
  { id: 7, name: 'Energy' }, { id: 8, name: 'Telecom' }, { id: 9, name: 'Realty' },
  { id: 10, name: 'Cement' }, { id: 11, name: 'Power' },
];

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

// ── New types for enhanced UI ──

export interface ActivityEvent {
  id: string;
  ts: string;
  type: 'NEW' | 'DROP' | 'TRIGGER' | 'T1' | 'ACTIVE' | 'INVALID' | 'JUMP_UP' | 'JUMP_DN' | 'STATE';
  symbol: string;
  direction: Direction;
  text: string;
  detail: string;
  cycle: number;
}

export interface ActiveThesisEntry {
  thesis_id: string;
  symbol: string;
  direction: Direction;
  setup_label: string;
  state: string;
  trigger: number;
  t1: number;
  t2: number;
  net_rr: number;
  mfe_R: number;
  mae_R: number;
  entry_price: number | null;
  current_price: number | null;
}

export interface CandleEntry {
  o: number;
  h: number;
  l: number;
  c: number;
}

export interface CandleOverlays {
  vwap: number;
  trigger: number;
  invalidation: number;
  t1: number;
  t2: number;
}

export interface CandleResponse {
  symbol: string;
  interval: string;
  candles: CandleEntry[];
  overlays?: CandleOverlays | null;
}

import type { DataSource } from '@/lib/apiFetch';

type WSEnvelope<T extends string, P> = {
  type: T;
  timestamp: string;
  source?: DataSource;
  payload: P;
};

export type WSMessage =
  | WSEnvelope<'L1_CONTEXT', MarketContextFrame>
  | WSEnvelope<'L6_RANKINGS', { long: RankingEntry[]; short: RankingEntry[] }>
  | WSEnvelope<'L8_THESIS', { thesis_id: string; card: ThesisCard }>
  | WSEnvelope<'L9_INVALIDATION', { thesis_id: string; reason: string }>
  | WSEnvelope<'L10_EDGE', { tier: number; promotion: string }>
  | WSEnvelope<'SUBSCRIBED', { channels: string[] }>;
