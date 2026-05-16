import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockFetch = vi.fn();
(globalThis as unknown as { fetch: typeof mockFetch }).fetch = mockFetch;

describe('useRankings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should export useRankings function', async () => {
    const { useRankings } = await import('./useRankings');
    expect(useRankings).toBeDefined();
    expect(typeof useRankings).toBe('function');
  });
});
