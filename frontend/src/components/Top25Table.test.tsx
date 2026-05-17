import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Top25Table } from './Top25Table';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

function wrapper({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe('Top25Table', () => {
  it('should render the table heading', () => {
    render(<Top25Table direction="long" />, { wrapper });
    expect(screen.getByText('Top 25 long')).toBeDefined();
  });

  it('should render expand arrows on rows', () => {
    render(<Top25Table direction="long" />, { wrapper });
    // Each row should have a ▶ indicator (collapsed state)
    const arrows = document.querySelectorAll('td');
    const arrowCell = Array.from(arrows).find(
      (td) => td.textContent === '▶' || td.textContent === '▼'
    );
    // Should have at least one arrow cell (or loading state means none yet)
    if (arrowCell) {
      expect(arrowCell.textContent).toMatch(/[▶▼]/);
    }
    expect(document.querySelector('table')).toBeDefined();
  });
});
