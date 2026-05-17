import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useMarketContext } from './useMarketContext';

const queryClient = new QueryClient();
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe('useMarketContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  it('should fetch from /api proxy', async () => {
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({ regime: 'Trending-Up', regime_confidence: 0.85, volatility_qualifier: 'Volatile', vix_band: 'Elevated', vix_trajectory: 'Rising', time_bucket: 'Opening', event_flag: null, breadth: 'Broad', premarket_bias: 'Bullish', bank_nifty_divergence: 0.0 }),
    } as Response);

    renderHook(() => useMarketContext(), { wrapper });
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/market/context');
    });
  });
});
