import { useMarketStore } from '@/stores/marketStore';
import { cn } from '@/lib/utils';
import { DataAgeBadge } from './DataAgeBadge';

function Badge({
  children,
  variant = 'neutral',
}: {
  children: React.ReactNode;
  variant?: 'long' | 'short' | 'neutral' | 'warn';
}) {
  const variantStyles = {
    long: 'bg-[var(--trade-long-dim)] text-[var(--trade-long)]',
    short: 'bg-[var(--trade-short-dim)] text-[var(--trade-short)]',
    neutral: 'bg-[var(--bg-surface-raised)] text-[var(--text-secondary)]',
    warn: 'bg-[var(--trade-neutral-dim)] text-[var(--trade-neutral)]',
  };
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md px-2 py-0.5 text-fluid-xs font-medium',
        variantStyles[variant]
      )}
    >
      {children}
    </span>
  );
}

export function RegimeBanner() {
  const ctx = useMarketStore((s) => s.context);
  const wsConnected = useMarketStore((s) => s.wsConnected);
  const ts = useMarketStore((s) => s.lastWSTimestamps['L1_CONTEXT']);

  if (!ctx) {
    return (
      <div
        role="status"
        aria-label="Loading market context"
        className="bg-surface rounded-lg border border-[var(--border-subtle)] p-[var(--space-md)] animate-pulse"
      >
        <div className="h-6 w-48 rounded bg-[var(--bg-surface-raised)]" />
      </div>
    );
  }

  const regimeVariant =
    ctx.regime === 'Trending-Up'
      ? 'long'
      : ctx.regime === 'Trending-Down'
        ? 'short'
        : 'warn';

  const vixVariant =
    ctx.vix_band === 'Elevated'
      ? 'warn'
      : ctx.vix_band === 'Compressed'
        ? 'long'
        : 'neutral';

  const breadthVariant =
    ctx.breadth === 'Strong'
      ? 'long'
      : ctx.breadth === 'Weak'
        ? 'short'
        : 'neutral';

  return (
    <div className="bg-surface rounded-lg border border-[var(--border-subtle)] p-[var(--space-sm)] md:p-[var(--space-md)]">
      <div className="flex flex-wrap items-center gap-[var(--space-xs)] md:gap-[var(--space-sm)]">
        {/* Regime — primary */}
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'inline-block h-2.5 w-2.5 rounded-full',
              regimeVariant === 'long' && 'bg-[var(--trade-long)]',
              regimeVariant === 'short' && 'bg-[var(--trade-short)]',
              regimeVariant === 'warn' && 'bg-[var(--trade-neutral)]'
            )}
          />
          <span className="text-fluid-lg font-bold">{ctx.regime}</span>
        </div>

        <div className="hidden h-4 w-px bg-[var(--border-subtle)] sm:block" />

        {/* Volatility qualifier */}
        <Badge variant={ctx.volatility_qualifier === 'Volatile' ? 'warn' : 'neutral'}>
          {ctx.volatility_qualifier}
        </Badge>

        {/* VIX */}
        <Badge variant={vixVariant}>VIX {ctx.vix_band}</Badge>

        {/* Breadth */}
        <Badge variant={breadthVariant}>Breadth {ctx.breadth}</Badge>

        {/* Premarket */}
        <Badge variant="neutral">Pre-market {ctx.premarket_bias}</Badge>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Time bucket + connection */}
        <div className="flex w-full items-center justify-between gap-3 sm:w-auto sm:justify-start">
          <span className="text-fluid-sm text-[var(--text-secondary)]">{ctx.time_bucket}</span>
          <DataAgeBadge timestamp={ts} />
          <span className="flex items-center gap-1.5 text-fluid-xs">
            <span
              className={cn(
                'h-1.5 w-1.5 rounded-full',
                wsConnected ? 'bg-[var(--trade-long)]' : 'bg-[var(--trade-short)]'
              )}
            />
            <span className={wsConnected ? 'text-[var(--trade-long)]' : 'text-[var(--trade-short)]'}>
              {wsConnected ? 'Live' : 'Offline'}
            </span>
          </span>
        </div>
      </div>
    </div>
  );
}
