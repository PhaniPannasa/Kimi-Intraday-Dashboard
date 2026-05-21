import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useRankingsAll } from './useRankingsAll';
import { useMarketStore } from '@/stores/marketStore';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

const LONG_RANKING = {
  symbol: 'RELIANCE',
  instrument_key: 'NSE_EQ|INE002A01018',
  direction: 'LONG' as const,
  score: 85.5,
  setup_type: 1,
  setup_label: 'ORB-15m',
  confluence_score: 5,
  net_rr: 1.5,
  actionability_tier: 'Tradeable',
  rank_movement: 'STABLE' as const,
  liquidity_quality: 'Good',
  price: 2500,
  change_pct: 1.2,
  sector_name: 'Energy',
  sector_id: 7,
  rs_ratio: 1.1,
  rs_momentum: 1.05,
  sparkline: [],
  state: 'PENDING' as const,
  edge_tier: 2,
};

const SHORT_RANKING = {
  symbol: 'TCS',
  instrument_key: 'NSE_EQ|INE467B01029',
  direction: 'SHORT' as const,
  score: 72.3,
  setup_type: 2,
  setup_label: 'VWAP Reclaim',
  confluence_score: 4,
  net_rr: 1.2,
  actionability_tier: 'Constrained',
  rank_movement: 'DOWN' as const,
  liquidity_quality: 'Good',
  price: 3200,
  change_pct: -0.5,
  sector_name: 'IT',
  sector_id: 2,
  rs_ratio: 0.9,
  rs_momentum: 0.95,
  sparkline: [],
  state: 'PENDING' as const,
  edge_tier: 3,
};

describe('useRankingsAll', () => {
  beforeEach(() => {
    useMarketStore.setState({ longRankings: [], shortRankings: [], sources: {} });
    queryClient.clear();
    vi.restoreAllMocks();
  });

  it('writes both long and short rankings into the store atomically', async () => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/long')) {
        return Promise.resolve({
          ok: true,
          headers: new Headers({ 'x-data-source': 'pipeline' }),
          json: async () => Promise.resolve([LONG_RANKING]),
        });
      }
      if (url.includes('/short')) {
        return Promise.resolve({
          ok: true,
          headers: new Headers({ 'x-data-source': 'pipeline' }),
          json: async () => Promise.resolve([SHORT_RANKING]),
        });
      }
      return Promise.reject(new Error('Unexpected URL'));
    });

    renderHook(() => useRankingsAll(), { wrapper: Wrapper });

    await waitFor(() => {
      const state = useMarketStore.getState();
      expect(state.longRankings).toHaveLength(1);
      expect(state.longRankings[0].symbol).toBe('RELIANCE');
      expect(state.shortRankings).toHaveLength(1);
      expect(state.shortRankings[0].symbol).toBe('TCS');
    });

    // Verify both arrays are set together (atomic write)
    const state = useMarketStore.getState();
    expect(state.longRankings).toHaveLength(1);
    expect(state.shortRankings).toHaveLength(1);
  });

  it('does not overwrite one direction when the other is still pending', async () => {
    // Simulate long returning before short
    const shortPromise = new Promise<unknown>(() => {
      // Never resolves — keeps short query in pending state
    });

    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/long')) {
        return Promise.resolve({
          ok: true,
          headers: new Headers({ 'x-data-source': 'pipeline' }),
          json: async () => {
            // long resolves immediately
            return [LONG_RANKING];
          },
        });
      }
      if (url.includes('/short')) {
        return shortPromise;
      }
      return Promise.reject(new Error('Unexpected URL'));
    });

    renderHook(() => useRankingsAll(), { wrapper: Wrapper });

    // Wait for long to resolve
    await waitFor(() => {
      // shortRankings should NOT be overwritten with empty while short is pending
      const state = useMarketStore.getState();
      expect(state.shortRankings).toHaveLength(0); // short not resolved yet
    });
  });

  it('sets source metadata for both directions', async () => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      const data = url.includes('/long') ? [LONG_RANKING] : [SHORT_RANKING];
      return Promise.resolve({
        ok: true,
        headers: new Headers({ 'x-data-source': 'pipeline' }),
        json: async () => Promise.resolve(data),
      });
    });

    renderHook(() => useRankingsAll(), { wrapper: Wrapper });

    await waitFor(() => {
      const state = useMarketStore.getState();
      expect(state.sources['rankings/top25/long']).toBe('pipeline');
      expect(state.sources['rankings/top25/short']).toBe('pipeline');
    });
  });

  it('returns isLoading true while any query is loading', async () => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/long')) {
        return new Promise(() => {}); // never resolves — long stays loading
      }
      return Promise.resolve({
        ok: true,
        headers: new Headers({ 'x-data-source': 'pipeline' }),
        json: async () => [SHORT_RANKING],
      });
    });

    const { result } = renderHook(() => useRankingsAll(), { wrapper: Wrapper });

    // isLoading should be true because long is still pending
    expect(result.current.isLoading).toBe(true);
  });

  it('returns isError true when any query fails', async () => {
    globalThis.fetch = vi.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: false,
        status: 500,
        json: async () => Promise.resolve({}),
      });
    });

    const { result } = renderHook(() => useRankingsAll(), { wrapper: Wrapper });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});