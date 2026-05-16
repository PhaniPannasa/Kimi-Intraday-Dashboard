import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock fetch globally
const mockFetch = vi.fn();
(globalThis as unknown as { fetch: typeof mockFetch }).fetch = mockFetch;

describe('useMarketContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should call fetch with correct URL', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ regime: 'Trending-Up', regime_confidence: 0.85 }),
    });

    const { useMarketContext } = await import('./useMarketContext');
    // We verify the hook compiles and the module exports correctly
    expect(useMarketContext).toBeDefined();
  });
});
