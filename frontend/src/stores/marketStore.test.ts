import { describe, it, expect } from 'vitest';
import { useMarketStore } from './marketStore';

describe('marketStore', () => {
  it('should initialize with null context', () => {
    const state = useMarketStore.getState();
    expect(state.context).toBeNull();
    expect(state.longRankings).toEqual([]);
    expect(state.shortRankings).toEqual([]);
    expect(state.selectedThesis).toBeNull();
    expect(state.wsConnected).toBe(false);
  });

  it('should update context via setContext', () => {
    const ctx = {
      regime: 'Trending-Up' as const,
      regime_confidence: 0.85,
      volatility_qualifier: 'Normal',
      vix_band: 'Normal',
      vix_trajectory: 'Stable',
      time_bucket: 'Trend Establishment',
      event_flag: null,
      breadth: 'Strong',
      premarket_bias: 'Positive',
      bank_nifty_divergence: 0,
    };
    useMarketStore.getState().setContext(ctx);
    expect(useMarketStore.getState().context).toEqual(ctx);
  });

  it('should update rankings via setRankings', () => {
    const long = [{ symbol: 'RELIANCE', instrument_key: 'NSE_EQ|INE002A01018', score: 84.5, setup_type: 1, confluence_score: 5, net_rr: 1.4, actionability_tier: 'Tradeable' as const, rank_movement: 'UP' as const, liquidity_quality: 'Excellent' }];
    const short: typeof long = [];
    useMarketStore.getState().setRankings(long, short);
    expect(useMarketStore.getState().longRankings).toEqual(long);
    expect(useMarketStore.getState().shortRankings).toEqual(short);
  });

  it('should update selectedThesis', () => {
    const thesis = {
      thesis_id: 'test-1',
      symbol: 'TCS',
      direction: 'LONG' as const,
      setup_type: 1,
      trigger: 2450.5,
      invalidation: 2420,
      t1: 2495,
      t2: 2530,
      gross_rr: 1.5,
      net_rr: 1.35,
      grade: 'ATTRACTIVE',
      time_decay_multiplier: 1.0,
      actionability_tier: 'Tradeable' as const,
      valid_until: '2026-05-16T00:00:00Z',
      preferred_regime: 'Trending-Up' as const,
    };
    useMarketStore.getState().setSelectedThesis(thesis);
    expect(useMarketStore.getState().selectedThesis).toEqual(thesis);
  });
});
