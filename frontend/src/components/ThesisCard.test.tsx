import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { ThesisPanel } from './ThesisCard';
import { useMarketStore } from '@/stores/marketStore';

describe('ThesisPanel', () => {
  beforeEach(() => {
    useMarketStore.setState({ selectedThesis: null });
  });

  afterEach(() => { cleanup(); });

  it('should show placeholder when no thesis selected', () => {
    render(<ThesisPanel />);
    expect(screen.getByText(/select a stock/i)).toBeDefined();
  });

  it('should show thesis details when selected', () => {
    useMarketStore.setState({
      selectedThesis: {
        thesis_id: 'test-1',
        symbol: 'RELIANCE',
        direction: 'LONG',
        setup_type: 1,
        trigger: 2450.5,
        invalidation: 2420,
        t1: 2495,
        t2: 2530,
        gross_rr: 1.5,
        net_rr: 1.35,
        grade: 'ATTRACTIVE',
        time_decay_multiplier: 1.0,
        actionability_tier: 'Tradeable',
        valid_until: '2026-05-16T00:00:00Z',
        preferred_regime: 'Trending-Up',
      },
    });
    render(<ThesisPanel />);
    expect(screen.getByText(/RELIANCE/)).toBeDefined();
  });
});
