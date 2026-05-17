import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useMarketStore } from '@/stores/marketStore';
import { useWebSocket } from './useWebSocket';

class MockWebSocket {
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  sent: string[] = [];
  close = vi.fn();
  send = vi.fn((data: string) => this.sent.push(data));
}

describe('useWebSocket', () => {
  let mockWs: MockWebSocket;

  beforeEach(() => {
    mockWs = new MockWebSocket();
    vi.stubGlobal('WebSocket', vi.fn(() => mockWs));
    useMarketStore.setState({ theses: [], invalidatedTheses: [], edgeTiers: {}, wsConnected: false });
  });

  afterEach(() => { vi.unstubAllGlobals(); });

  it('should handle L8_THESIS messages', () => {
    renderHook(() => useWebSocket());
    mockWs.onopen?.();
    mockWs.onmessage?.({ data: JSON.stringify({
      type: 'L8_THESIS', timestamp: '2026-05-17T09:30:00Z',
      payload: { thesis_id: 't1', card: { thesis_id: 't1', symbol: 'RELIANCE', direction: 'LONG', setup_type: 1, trigger: 2500, invalidation: 2450, t1: 2550, t2: 2600, gross_rr: 2.0, net_rr: 1.8, grade: 'ATTRACTIVE', time_decay_multiplier: 1.0, actionability_tier: 'Tradeable', valid_until: '2026-05-17T10:00:00Z', preferred_regime: 'Trending-Up' } },
    })});
    expect(useMarketStore.getState().theses).toHaveLength(1);
  });

  it('should handle L9_INVALIDATION messages', () => {
    renderHook(() => useWebSocket());
    mockWs.onopen?.();
    useMarketStore.getState().addOrUpdateThesis({ thesis_id: 't2', symbol: 'INFY', direction: 'SHORT', setup_type: 1, trigger: 1500, invalidation: 1550, t1: 1450, t2: 1400, gross_rr: 1.5, net_rr: 1.3, grade: 'MARGINAL', time_decay_multiplier: 0.9, actionability_tier: 'Constrained', valid_until: '2026-05-17T10:00:00Z', preferred_regime: 'Trending-Down' });
    mockWs.onmessage?.({ data: JSON.stringify({ type: 'L9_INVALIDATION', timestamp: '2026-05-17T09:35:00Z', payload: { thesis_id: 't2', reason: 'Stop loss hit' } }) });
    expect(useMarketStore.getState().invalidatedTheses).toHaveLength(1);
  });

  it('should handle L10_EDGE messages', () => {
    renderHook(() => useWebSocket());
    mockWs.onopen?.();
    mockWs.onmessage?.({ data: JSON.stringify({ type: 'L10_EDGE', timestamp: '2026-05-17T09:40:00Z', payload: { tier: 3, promotion: 'PROMOTED' } }) });
    expect(useMarketStore.getState().edgeTiers[3]).toBe('PROMOTED');
  });
});
