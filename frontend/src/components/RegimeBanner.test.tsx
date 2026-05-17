import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { RegimeBanner } from './RegimeBanner';
import { useMarketStore } from '@/stores/marketStore';

describe('RegimeBanner', () => {
  beforeEach(() => {
    useMarketStore.setState({ context: null });
  });

  afterEach(() => { cleanup(); });

  it('should show loading when context is null', () => {
    render(<RegimeBanner />);
    expect(screen.getByText(/loading/i)).toBeDefined();
  });

  it('should show regime when context is set', () => {
    useMarketStore.setState({
      context: {
        regime: 'Trending-Up',
        regime_confidence: 0.85,
        volatility_qualifier: 'Volatile',
        vix_band: 'Elevated',
        vix_trajectory: 'Rising',
        time_bucket: 'Trend Establishment',
        event_flag: null,
        breadth: 'Strong',
        premarket_bias: 'Positive',
        bank_nifty_divergence: 0,
      },
    });
    render(<RegimeBanner />);
    expect(screen.getByText('Trending-Up')).toBeDefined();
  });
});
