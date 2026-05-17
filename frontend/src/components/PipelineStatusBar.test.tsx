import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PipelineStatusBar } from './PipelineStatusBar';

const queryClient = new QueryClient();

describe('PipelineStatusBar', () => {
  it('should render loading skeleton', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <PipelineStatusBar />
      </QueryClientProvider>
    );
    expect(document.querySelector('.animate-pulse')).toBeDefined();
  });
});
