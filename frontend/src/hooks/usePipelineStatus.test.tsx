import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { usePipelineStatus } from './usePipelineStatus';

const queryClient = new QueryClient();
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe('usePipelineStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  it('fetches from /api/pipeline/status and reports source', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'X-Data-Source': 'mock' }),
      json: async () => ({
        cycle_number: 1,
        phase: 'closed',
        layers: { l1_market_context: { status: 'ok', duration_ms: 12 } },
      }),
    } as Response);

    const { result } = renderHook(() => usePipelineStatus(), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.source).toBe('mock');
  });
});
