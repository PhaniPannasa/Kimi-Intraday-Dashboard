import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useFunnelCounts } from './useFunnelCounts';
import { useActiveTheses } from './useActiveTheses';
import { useEdgeTiers } from './useEdgeTiers';
import { useActivityEvents } from './useActivityEvents';
import { useMarketStore } from '@/stores/marketStore';

const queryClient = new QueryClient();
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

function mockOnce(body: unknown, source = 'mock') {
  vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
    ok: true,
    headers: new Headers({ 'X-Data-Source': source }),
    json: async () => body,
  } as Response);
}

describe('new REST hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
    useMarketStore.setState({
      activeTheses: [],
      edgeTiers: {},
      edgeTiersFull: {},
      sources: {},
    });
  });

  it('useFunnelCounts hits /api/funnel/counts', async () => {
    mockOnce({ L1: { in_count: 1, out_count: 1, layer: 'L1' } });
    const { result } = renderHook(() => useFunnelCounts(), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/funnel/counts');
  });

  it('useActiveTheses hits /api/monitor/active-theses', async () => {
    mockOnce({ theses: [] });
    const { result } = renderHook(() => useActiveTheses(), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/monitor/active-theses');
  });

  it('useActiveTheses writes fetched theses into the Zustand store', async () => {
    const theses = [
      {
        thesis_id: 't-rest-1',
        symbol: 'RELIANCE',
        direction: 'LONG' as const,
        setup_label: 'Pullback-EMA20',
        state: 'TRIGGERED',
        trigger: 2502.5,
        t1: 2540,
        t2: 2580,
        net_rr: 1.6,
        mfe_R: 0.4,
        mae_R: -0.1,
        entry_price: 2505.0,
        current_price: 2516.3,
      },
    ];
    mockOnce({ theses }, 'pipeline');
    const { result } = renderHook(() => useActiveTheses(), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());

    await waitFor(() => {
      expect(useMarketStore.getState().activeTheses).toHaveLength(1);
    });
    expect(useMarketStore.getState().activeTheses[0].thesis_id).toBe('t-rest-1');
    expect(useMarketStore.getState().sources['monitor/active-theses']).toBe('pipeline');
  });

  it('useEdgeTiers hits /api/edge/tiers', async () => {
    mockOnce({ tiers: [], promotions: [] });
    const { result } = renderHook(() => useEdgeTiers(), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/edge/tiers');
  });

  it('useEdgeTiers writes fetched tiers into the Zustand store', async () => {
    const tiers = [
      {
        tier_id: 1,
        label: 'T1',
        setup_type: 1,
        regime: 'Trending-Up',
        direction: 'LONG',
        n: 120,
        hit_rate: 0.625,
        ci_lower: 0.54,
        ci_upper: 0.71,
        is_significant: true,
        avg_net_return: 0.85,
        std_net_return: 1.2,
        live_count: 3,
      },
      {
        tier_id: 3,
        // no label — exercise the derived-summary path
        setup_type: 2,
        regime: 'Range-Bound',
        direction: 'SHORT',
        n: 80,
        hit_rate: 0.42,
        ci_lower: 0.32,
        ci_upper: 0.52,
        is_significant: false,
        avg_net_return: 0.1,
        std_net_return: 0.9,
        live_count: 1,
      },
    ];
    mockOnce({ tiers, promotions: [1] }, 'pipeline');
    const { result } = renderHook(() => useEdgeTiers(), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());

    await waitFor(() => {
      expect(Object.keys(useMarketStore.getState().edgeTiersFull)).toHaveLength(2);
    });
    const state = useMarketStore.getState();
    expect(state.edgeTiersFull[1].label).toBe('T1');
    expect(state.edgeTiersFull[3].n).toBe(80);
    // edgeTiers (string map) is populated with label or summary
    expect(state.edgeTiers[1]).toBe('T1');
    expect(state.edgeTiers[3]).toMatch(/n=80/);
    expect(state.sources['edge/tiers']).toBe('pipeline');
  });

  it('useActivityEvents hits /api/activity/events with since=0', async () => {
    mockOnce({ events: [], total: 0 });
    const { result } = renderHook(() => useActivityEvents(), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/activity/events?since=0&limit=20');
  });
});
