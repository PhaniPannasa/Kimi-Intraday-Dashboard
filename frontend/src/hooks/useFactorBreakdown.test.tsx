import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useFactorBreakdown } from './useFactorBreakdown';

const queryClient = new QueryClient();
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe('useFactorBreakdown', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  it('fetches from /api/rankings/RELIANCE/factors and reports source', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'X-Data-Source': 'mock' }),
      json: async () => ({ symbol: 'RELIANCE', direction: 'LONG', factors: [] }),
    } as Response);

    const { result } = renderHook(() => useFactorBreakdown('RELIANCE'), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.source).toBe('mock');
  });

  it('does not fetch when symbol is null', () => {
    vi.spyOn(globalThis, 'fetch');
    renderHook(() => useFactorBreakdown(null), { wrapper });
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });
});
