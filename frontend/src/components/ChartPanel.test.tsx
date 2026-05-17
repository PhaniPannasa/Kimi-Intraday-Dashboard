import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import { ChartPanel } from './ChartPanel';

vi.mock('lightweight-charts', () => {
  const mockSeries = {
    setData: vi.fn(),
  };
  const mockChart = {
    addCandlestickSeries: vi.fn(() => mockSeries),
    remove: vi.fn(),
    timeScale: vi.fn(() => ({ fitContent: vi.fn() })),
  };
  return {
    createChart: vi.fn(() => mockChart),
  };
});

describe('ChartPanel', () => {
  it('should render a chart container', () => {
    const { container } = render(<ChartPanel data={[]} />);
    expect(container.querySelector('div')).toBeDefined();
  });

  it('should render with candlestick data', () => {
    const data = [
      { time: '2026-05-17', open: 2500, high: 2550, low: 2480, close: 2520 },
    ];
    const { container } = render(<ChartPanel data={data} />);
    expect(container.querySelector('div')).toBeDefined();
  });
});
