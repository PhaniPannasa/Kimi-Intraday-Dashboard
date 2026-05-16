import { describe, it, expect } from 'vitest';

describe('useWebSocket', () => {
  it('should export useWebSocket function', async () => {
    const { useWebSocket } = await import('./useWebSocket');
    expect(useWebSocket).toBeDefined();
    expect(typeof useWebSocket).toBe('function');
  });
});
