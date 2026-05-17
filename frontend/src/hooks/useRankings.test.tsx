import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useRankings } from './useRankings';

const queryClient = new QueryClient();
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe('useRankings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  it('should fetch from /api proxy', async () => {
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => [{ symbol: 'RELIANCE', score: 85, instrument_key: 'NSE_EQ|RELIANCE' }],
    } as Response);

    renderHook(() => useRankings('long'), { wrapper });
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/rankings/top25/long');
    });
  });
});
