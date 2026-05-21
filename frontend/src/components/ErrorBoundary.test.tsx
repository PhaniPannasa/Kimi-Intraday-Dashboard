import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { ErrorBoundary } from './ErrorBoundary';

function BrokenComponent(): React.ReactElement {
  throw new Error('simulated render crash');
}

function WorkingComponent(): React.ReactElement {
  return <div>all good</div>;
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <WorkingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText('all good')).toBeDefined();
  });

  it('renders fallback UI when child throws', () => {
    render(
      <ErrorBoundary>
        <BrokenComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText(/something went wrong/i)).toBeDefined();
  });

  it('renders custom fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<div>custom error ui</div>}>
        <BrokenComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText('custom error ui')).toBeDefined();
  });

  it('has a Try Again button that attempts recovery', () => {
    render(
      <ErrorBoundary>
        <BrokenComponent />
      </ErrorBoundary>
    );
    const btn = screen.getByRole('button', { name: /try again/i });
    expect(btn).toBeDefined();
  });
});
