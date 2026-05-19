import { useMarketStore } from '@/stores/marketStore';
import { cn } from '@/lib/utils';

export function RegimeBanner() {
  const ctx = useMarketStore((s) => s.context);

  if (!ctx) {
    return (
      <div className="flex h-12 items-center border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 animate-pulse">
        <div className="h-4 w-64 rounded bg-[var(--bg-surface-raised)]" />
      </div>
    );
  }

  const regimeColor =
    ctx.regime === 'Trending-Up'
      ? 'var(--trade-long)'
      : ctx.regime === 'Trending-Down'
        ? 'var(--trade-short)'
        : 'var(--trade-neutral)';

  const vixChipClass =
    ctx.vix_band === 'Elevated'
      ? 'bg-[var(--trade-neutral-dim)] text-[var(--trade-neutral)]'
      : ctx.vix_band === 'Compressed'
        ? 'bg-[var(--trade-long-dim)] text-[var(--trade-long)]'
        : 'bg-[var(--bg-surface-raised)] text-[var(--text-secondary)]';

  const breadthChipClass =
    ctx.breadth === 'Strong'
      ? 'bg-[var(--trade-long-dim)] text-[var(--trade-long)]'
      : ctx.breadth === 'Weak'
        ? 'bg-[var(--trade-short-dim)] text-[var(--trade-short)]'
        : 'bg-[var(--bg-surface-raised)] text-[var(--text-secondary)]';

  const biasChipClass =
    ctx.premarket_bias === 'Positive'
      ? 'bg-[var(--trade-long-dim)] text-[var(--trade-long)]'
      : ctx.premarket_bias === 'Negative'
        ? 'bg-[var(--trade-short-dim)] text-[var(--trade-short)]'
        : 'bg-[var(--bg-surface-raised)] text-[var(--text-secondary)]';

  return (
    <div
      className="flex flex-wrap items-center gap-3 border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2.5 md:gap-4 md:px-4"
    >
      {/* Regime + confidence */}
      <div className="flex items-center gap-2">
        <span
          className="inline-block h-2 w-2 rounded-full"
          style={{
            background: regimeColor,
            boxShadow: `0 0 12px ${regimeColor}`,
          }}
        />
        <div className="flex flex-col leading-tight">
          <span className="text-[10px] uppercase tracking-wide text-[var(--text-tertiary)]">
            L1 Regime
          </span>
          <span
            className="text-lg font-bold tracking-tight"
            style={{ color: regimeColor }}
          >
            {ctx.regime}
          </span>
        </div>
        <span className="font-mono text-[11px] text-[var(--text-tertiary)]">
          {(ctx.regime_confidence * 100).toFixed(0)}%
        </span>
      </div>

      <div className="hidden h-8 w-px bg-[var(--border-subtle)] md:block" />

      {/* VIX */}
      <div className="flex flex-col leading-tight">
        <span className="text-[10px] uppercase tracking-wide text-[var(--text-tertiary)]">
          India VIX
        </span>
        <div className="flex items-baseline gap-1.5">
          <span className="font-mono text-base font-semibold tabular-nums">
            {ctx.vix_value.toFixed(2)}
          </span>
          <span className={cn('rounded px-1.5 py-0.5 text-[10px] font-semibold', vixChipClass)}>
            {ctx.vix_band}
          </span>
          <span className="text-[10px]">
            {ctx.vix_trajectory === 'Rising' ? '↑' : '↓'}
          </span>
        </div>
      </div>

      <div className="hidden h-8 w-px bg-[var(--border-subtle)] md:block" />

      {/* Breadth */}
      <div className="flex flex-col leading-tight">
        <span className="text-[10px] uppercase tracking-wide text-[var(--text-tertiary)]">
          Breadth
        </span>
        <span className={cn('rounded px-1.5 py-0.5 text-[10px] font-semibold', breadthChipClass)}>
          {ctx.breadth}
        </span>
      </div>

      {/* Premarket bias - hidden on mobile */}
      <div className="hidden items-center gap-3 lg:flex">
        <div className="h-8 w-px bg-[var(--border-subtle)]" />
        <div className="flex flex-col leading-tight">
          <span className="text-[10px] uppercase tracking-wide text-[var(--text-tertiary)]">
            Pre-market
          </span>
          <span className={cn('rounded px-1.5 py-0.5 text-[10px] font-semibold', biasChipClass)}>
            {ctx.premarket_bias}
          </span>
        </div>
      </div>

      {/* BankNifty Divergence - hidden on mobile */}
      {Math.abs(ctx.bank_nifty_divergence) > 0 && (
        <div className="hidden items-center gap-3 lg:flex">
          <div className="h-8 w-px bg-[var(--border-subtle)]" />
          <div className="flex flex-col leading-tight">
            <span className="text-[10px] uppercase tracking-wide text-[var(--text-tertiary)]">
              BankNifty Δ
            </span>
            <span
              className={cn(
                'font-mono text-sm font-semibold tabular-nums',
                ctx.bank_nifty_divergence > 0.2
                  ? 'text-[var(--trade-long)]'
                  : ctx.bank_nifty_divergence < -0.2
                    ? 'text-[var(--trade-short)]'
                    : 'text-[var(--text-primary)]'
              )}
            >
              {ctx.bank_nifty_divergence >= 0 ? '+' : ''}
              {ctx.bank_nifty_divergence.toFixed(2)}%
            </span>
          </div>
        </div>
      )}

      {/* Event flag */}
      {ctx.event_flag && (
        <>
          <div className="h-8 w-px bg-[var(--border-subtle)]" />
          <div
            className="flex items-center gap-1.5 rounded px-2 py-1 text-[11px] font-semibold"
            style={{
              background: 'var(--trade-neutral-dim)',
              color: 'var(--trade-neutral)',
            }}
          >
            <svg width="11" height="11" viewBox="0 0 11 11">
              <path d="M5.5 1L10 9H1z" fill="currentColor" />
              <rect x="5" y="4" width="1" height="3" fill="var(--bg-surface)" />
              <rect x="5" y="7.5" width="1" height="1" fill="var(--bg-surface)" />
            </svg>
            <span className="text-[10px] uppercase tracking-wide">Event</span>
            <span>{ctx.event_flag}</span>
          </div>
        </>
      )}

      <div className="flex-1" />

      {/* Session bucket */}
      <div className="flex flex-col items-end leading-tight">
        <span className="text-[10px] uppercase tracking-wide text-[var(--text-tertiary)]">
          Session
        </span>
        <span className="text-sm font-semibold">{ctx.time_bucket}</span>
      </div>
    </div>
  );
}