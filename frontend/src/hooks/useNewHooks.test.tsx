import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useFunnelCounts } from './useFunnelCounts';
import { useActiveTheses } from './useActiveTheses';
import { useEdgeTiers } from './useEdgeTiers';
import { useActivityEvents } from './useActivityEvents';
import { useCandles } from './useCandles';

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

  it('useEdgeTiers hits /api/edge/tiers', async () => {
    mockOnce({ tiers: [], promotions: [] });
    const { result } = renderHook(() => useEdgeTiers(), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/edge/tiers');
  });

  it('useActivityEvents hits /api/activity/events with since=0', async () => {
    mockOnce({ events: [], total: 0 });
    const { result } = renderHook(() => useActivityEvents(), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/activity/events?since=0&limit=20');
  });

  it('useCandles(RELIANCE) hits /api/market/candles/RELIANCE', async () => {
    mockOnce({ symbol: 'RELIANCE', candles: [] });
    const { result } = renderHook(() => useCandles('RELIANCE'), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/market/candles/RELIANCE');
  });
});
