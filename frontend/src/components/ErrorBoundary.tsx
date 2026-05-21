'use client';

import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    if (import.meta.env.DEV) {
      console.error('[ErrorBoundary]', error.message, info.componentStack);
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="flex min-h-[200px] items-center justify-center rounded-lg border border-dashed border-[var(--trade-short-soft)] bg-[var(--bg-surface)] p-6">
          <div className="text-center">
            <div className="text-sm font-semibold text-[var(--trade-short)]">
              Something went wrong
            </div>
            <div className="mt-1 max-w-md text-[11px] text-[var(--text-tertiary)]">
              {this.state.error?.message}
            </div>
            <button
              onClick={this.handleReset}
              className="mt-3 rounded bg-[var(--bg-surface-raised)] px-4 py-1.5 text-[11px] font-bold text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-base)]"
            >
              Try Again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
