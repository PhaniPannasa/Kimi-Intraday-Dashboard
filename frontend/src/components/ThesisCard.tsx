import { useMarketStore } from '@/stores/marketStore';
import { cn } from '@/lib/utils';
import { DataAgeBadge } from './DataAgeBadge';
import { setupTypeLabels } from '@/types/api';

function Field({
  label,
  children,
  highlight = false,
}: {
  label: string;
  children: React.ReactNode;
  highlight?: boolean;
}) {
  return (
    <div className={cn('rounded-md p-2', highlight ? 'bg-[var(--bg-surface-raised)]' : '')}>
      <div className="text-fluid-xs text-[var(--text-tertiary)]">{label}</div>
      <div className="mt-0.5 text-fluid-sm font-medium tabular-nums">{children}</div>
    </div>
  );
}

export function ThesisPanel() {
  const thesis = useMarketStore((s) => s.selectedThesis);
  const ts = useMarketStore((s) => s.lastWSTimestamps['L8_THESIS']);

  if (!thesis) {
    return (
      <div className="flex min-h-[200px] flex-col items-center justify-center rounded-lg border border-dashed border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 text-center">
        <div className="text-fluid-lg text-[var(--text-tertiary)]">Select a stock</div>
        <div className="mt-1 text-fluid-sm text-[var(--text-secondary)]">
          Click any row in the rankings to view its thesis card
        </div>
      </div>
    );
  }

  const isLong = thesis.direction === 'LONG';
  const gradeColor =
    thesis.grade === 'ATTRACTIVE'
      ? 'text-[var(--trade-long)]'
      : thesis.grade === 'MARGINAL'
        ? 'text-[var(--trade-neutral)]'
        : 'text-[var(--trade-short)]';

  const gradeBg =
    thesis.grade === 'ATTRACTIVE'
      ? 'bg-[var(--trade-long-dim)]'
      : thesis.grade === 'MARGINAL'
        ? 'bg-[var(--trade-neutral-dim)]'
        : 'bg-[var(--trade-short-dim)]';

  return (
    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
      {/* Header */}
      <div
        className={cn(
          'flex items-center justify-between border-b border-[var(--border-subtle)] px-3 py-2 md:px-4 md:py-3',
          isLong ? 'bg-[var(--trade-long)]/5' : 'bg-[var(--trade-short)]/5'
        )}
      >
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'h-2 w-2 rounded-full',
              isLong ? 'bg-[var(--trade-long)]' : 'bg-[var(--trade-short)]'
            )}
          />
          <h2 className="text-fluid-base font-bold">
            {thesis.symbol}{' '}
            <span className={cn('text-fluid-sm font-medium', isLong ? 'text-[var(--trade-long)]' : 'text-[var(--trade-short)]')}>
              {thesis.direction}
            </span>
          </h2>
        </div>
        <span
          className={cn(
            'rounded px-2 py-0.5 text-fluid-xs font-bold',
            gradeBg,
            gradeColor
          )}
        >
          {thesis.grade}
        </span>
        <DataAgeBadge timestamp={ts} />
      </div>

      {/* Body */}
      <div className="p-3 md:p-4">
        {/* Primary metrics */}
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <Field label="Trigger" highlight>
            {thesis.trigger.toFixed(2)}
          </Field>
          <Field label="Invalidation" highlight>
            <span className={isLong ? 'text-[var(--trade-short)]' : 'text-[var(--trade-long)]'}>
              {thesis.invalidation.toFixed(2)}
            </span>
          </Field>
          <Field label="Net R:R" highlight>
            <span className={thesis.net_rr >= 1 ? 'text-[var(--trade-long)]' : 'text-[var(--trade-neutral)]'}>
              {thesis.net_rr.toFixed(2)}
            </span>
          </Field>
          <Field label="T1">{thesis.t1.toFixed(2)}</Field>
          <Field label="T2">{thesis.t2.toFixed(2)}</Field>
          <Field label="Gross R:R">{thesis.gross_rr.toFixed(2)}</Field>
        </div>

        {/* Divider */}
        <div className="my-3 h-px bg-[var(--border-subtle)]" />

        {/* Secondary metrics */}
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <Field label="Setup">{setupTypeLabels[thesis.setup_type] ?? thesis.setup_type}</Field>
          <Field label="Confluence">
            {thesis.confluence_score}
            <span className="text-[var(--text-tertiary)]">/6</span>
          </Field>
          <Field label="Time Decay">×{thesis.time_decay_multiplier.toFixed(2)}</Field>
          <Field label="Preferred Regime">{thesis.preferred_regime}</Field>
          <Field label="Tier">{thesis.actionability_tier}</Field>
          <Field label="Valid Until">
            {new Date(thesis.valid_until).toLocaleTimeString('en-IN', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </Field>
        </div>
      </div>
    </div>
  );
}
