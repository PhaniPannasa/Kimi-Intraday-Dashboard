import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useRankings } from './useRankings';
import { useMarketStore } from '@/stores/marketStore';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('useRankings', () => {
  beforeEach(() => {
    useMarketStore.setState({ longRankings: [], shortRankings: [] });
    queryClient.clear();
  });

  it('writes fetched long rankings into the store', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'x-data-source': 'pipeline' }),
      json: async () =>
        Promise.resolve([
          {
            symbol: 'RELIANCE',
            instrument_key: 'NSE_EQ|INE002A01018',
            direction: 'LONG',
            score: 85.5,
            setup_type: 1,
            setup_label: 'ORB-15m',
            confluence_score: 5,
            net_rr: 1.5,
            actionability_tier: 'Tradeable',
            rank_movement: 'STABLE',
            liquidity_quality: 'Good',
            price: 2500,
            change_pct: 1.2,
            sector_name: 'Energy',
            sector_id: 7,
            rs_ratio: 1.1,
            rs_momentum: 1.05,
            sparkline: [],
            state: 'PENDING',
            edge_tier: 2,
          },
        ]),
    });

    renderHook(() => useRankings('long'), { wrapper: Wrapper });

    await waitFor(() => {
      const state = useMarketStore.getState();
      expect(state.longRankings).toHaveLength(1);
      expect(state.longRankings[0].symbol).toBe('RELIANCE');
    });
  });

  it('writes fetched short rankings into the store', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'x-data-source': 'pipeline' }),
      json: async () =>
        Promise.resolve([
          {
            symbol: 'TCS',
            instrument_key: 'NSE_EQ|INE467B01029',
            direction: 'SHORT',
            score: 72.3,
            setup_type: 2,
            setup_label: 'VWAP Reclaim',
            confluence_score: 4,
            net_rr: 1.2,
            actionability_tier: 'Constrained',
            rank_movement: 'DOWN',
            liquidity_quality: 'Good',
            price: 3200,
            change_pct: -0.5,
            sector_name: 'IT',
            sector_id: 2,
            rs_ratio: 0.9,
            rs_momentum: 0.95,
            sparkline: [],
            state: 'PENDING',
            edge_tier: 3,
          },
        ]),
    });

    renderHook(() => useRankings('short'), { wrapper: Wrapper });

    await waitFor(() => {
      const state = useMarketStore.getState();
      expect(state.shortRankings).toHaveLength(1);
      expect(state.shortRankings[0].symbol).toBe('TCS');
    });
  });
});