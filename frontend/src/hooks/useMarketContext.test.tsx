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
});
