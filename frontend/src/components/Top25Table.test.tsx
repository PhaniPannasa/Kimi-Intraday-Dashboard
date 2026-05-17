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
});
