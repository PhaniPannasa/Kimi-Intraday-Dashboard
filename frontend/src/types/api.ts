export type Regime = 'Trending-Up' | 'Trending-Down' | 'Range-Bound';
export type Direction = 'LONG' | 'SHORT';
export type RankMovement = 'NEW' | 'UP' | 'DOWN' | 'STABLE';
export type ActionabilityTier = 'Tradeable' | 'Constrained' | 'Research-Only';

export interface MarketContextFrame {
  regime: Regime;
  regime_confidence: number;
  volatility_qualifier: string;
  vix_band: string;
  vix_trajectory: string;
  time_bucket: string;
  event_flag: string | null;
  breadth: string;
  premarket_bias: string;
  bank_nifty_divergence: number;
}

export interface RankingEntry {
  symbol: string;
  instrument_key: string;
  score: number;
  setup_type: number;
  confluence_score: number;
  net_rr: number;
  actionability_tier: ActionabilityTier;
  rank_movement: RankMovement;
  liquidity_quality: string;
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
  time_decay_multiplier: number;
  actionability_tier: ActionabilityTier;
  valid_until: string;
  preferred_regime: Regime;
}

export type WSMessage =
  | { type: 'L1_CONTEXT'; timestamp: string; payload: MarketContextFrame }
  | { type: 'L6_RANKINGS'; timestamp: string; payload: { long: RankingEntry[]; short: RankingEntry[] } }
  | { type: 'L8_THESIS'; timestamp: string; payload: { thesis_id: string; card: ThesisCard } }
  | { type: 'L9_INVALIDATION'; timestamp: string; payload: { thesis_id: string; reason: string } }
  | { type: 'L10_EDGE'; timestamp: string; payload: { tier: number; promotion: string } };
