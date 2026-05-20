import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useMarketContext } from './useMarketContext';
import { useMarketStore } from '@/stores/marketStore';

const queryClient = new QueryClient();
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe('useMarketContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
    useMarketStore.setState({ context: null, sources: {} });
  });

  it('captures source from response header', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'X-Data-Source': 'mock' }),
      json: async () => ({ regime: 'Range-Bound', vix_value: 15 }),
    } as Response);

    const { result } = renderHook(() => useMarketContext(), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.source).toBe('mock');
  });

  it('writes fetched context into the Zustand store', async () => {
    const payload = {
      regime: 'Trending-Up',
      regime_confidence: 0.82,
      volatility_qualifier: 'Normal',
      vix_band: 'Normal',
      vix_trajectory: 'Stable',
      vix_value: 14.2,
      time_bucket: 'Trend Establishment',
      event_flag: null,
      breadth: 'Strong',
      premarket_bias: 'Positive',
      bank_nifty_divergence: 0,
    };
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'X-Data-Source': 'pipeline' }),
      json: async () => payload,
    } as Response);

    const { result } = renderHook(() => useMarketContext(), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());

    // Both the source AND the context payload should be in the store.
    await waitFor(() => {
      expect(useMarketStore.getState().context).toEqual(payload);
    });
    expect(useMarketStore.getState().sources['market/context']).toBe('pipeline');
  });
});
