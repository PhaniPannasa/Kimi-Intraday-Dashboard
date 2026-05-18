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
    expect(state.lastWSTimestamps).toEqual({});
  });

  it('should update context via setContext', () => {
    const ctx = {
      regime: 'Trending-Up' as const,
      regime_confidence: 0.85,
      volatility_qualifier: 'Normal',
      vix_band: 'Normal' as const,
      vix_trajectory: 'Stable',
      time_bucket: 'Trend Establishment',
      event_flag: null,
      breadth: 'Strong' as const,
      premarket_bias: 'Positive',
      bank_nifty_divergence: 0,
      vix_value: 15.5,
    };
    useMarketStore.getState().setContext(ctx);
    expect(useMarketStore.getState().context).toEqual(ctx);
  });

  it('should update rankings via setRankings', () => {
    const long = [{ symbol: 'RELIANCE', instrument_key: 'NSE_EQ|INE002A01018', score: 84.5, setup_type: 1, confluence_score: 5, net_rr: 1.4, actionability_tier: 'Tradeable' as const, rank_movement: 'UP' as const, liquidity_quality: 'Excellent' as const, direction: 'LONG' as const }];
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
      confluence_score: 5,
      time_decay_multiplier: 1.0,
      actionability_tier: 'Tradeable' as const,
      valid_until: '2026-05-16T00:00:00Z',
      preferred_regime: 'Trending-Up' as const,
    };
    useMarketStore.getState().setSelectedThesis(thesis);
    expect(useMarketStore.getState().selectedThesis).toEqual(thesis);
  });

  it('should add or update a thesis', () => {
    useMarketStore.setState({ theses: [] });
    const store = useMarketStore.getState();
    store.addOrUpdateThesis({
      thesis_id: 't1', symbol: 'RELIANCE', direction: 'LONG', setup_type: 1,
      trigger: 2500, invalidation: 2450, t1: 2550, t2: 2600,
      gross_rr: 2.0, net_rr: 1.8, grade: 'ATTRACTIVE', confluence_score: 5,
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
      gross_rr: 1.5, net_rr: 1.3, grade: 'MARGINAL', confluence_score: 3,
      time_decay_multiplier: 0.9, actionability_tier: 'Constrained',
      valid_until: '2026-05-17T10:00:00Z', preferred_regime: 'Trending-Down',
    });
    store.invalidateThesis('t2', 'Stop loss hit');
    expect(useMarketStore.getState().invalidatedTheses).toContainEqual(
      expect.objectContaining({ thesis_id: 't2', reason: 'Stop loss hit' })
    );
  });

  it('should update edge tier', () => {
    const store = useMarketStore.getState();
    store.updateEdgeTier(1, 'PROMOTED');
    expect(useMarketStore.getState().edgeTiers[1]).toBe('PROMOTED');
  });

  it('should track WS timestamps via setWSTimestamp', () => {
    useMarketStore.setState({ lastWSTimestamps: {} });
    const store = useMarketStore.getState();
    store.setWSTimestamp('L1_CONTEXT', '2026-05-17T09:15:00Z');
    store.setWSTimestamp('L6_RANKINGS', '2026-05-17T09:15:01Z');
    expect(useMarketStore.getState().lastWSTimestamps).toEqual({
      L1_CONTEXT: '2026-05-17T09:15:00Z',
      L6_RANKINGS: '2026-05-17T09:15:01Z',
    });
  });
});
