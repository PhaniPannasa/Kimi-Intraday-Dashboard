import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DataSourceDebugPanel } from './DataSourceDebugPanel';
import React from 'react';

const queryClient = new QueryClient();
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe('DataSourceDebugPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      headers: new Headers({}),
      json: async () => ({
        timestamp: '2026-05-19T17:30:00Z',
        endpoints: {
          '/market/context': 'mock',
          '/rankings/top25/long': 'mock',
        },
        pipeline: {
          phase: 'closed',
          last_cycle_at: null,
          last_bar_at: null,
          symbols_feeding: 0,
          ws_connections: 1,
          scheduler_running: true,
        },
        layers: {
          l1_real: false, l2_real: false, l3_real: false, l4_real: false,
          l5_real: false, l6_real: false, l7_real: false, l8_real: false,
          l9_real: false, l10_real: false,
        },
      }),
    } as Response);
  });
  afterEach(() => { cleanup(); });

  it('renders pipeline phase and symbols_feeding when expanded', async () => {
    render(<DataSourceDebugPanel defaultOpen={true} />, { wrapper });
    expect(await screen.findByText(/closed/i)).toBeDefined();
    expect(screen.getByText(/symbols_feeding/i)).toBeDefined();
  });

  it('renders collapsed by default', () => {
    render(<DataSourceDebugPanel />, { wrapper });
    expect(screen.getByRole('button', { name: /truth/i })).toBeDefined();
  });
});
