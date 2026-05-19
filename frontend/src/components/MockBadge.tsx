import type { DataSource } from '@/lib/apiFetch';

interface MockBadgeProps {
  source: DataSource | undefined;
  className?: string;
}

const LABEL: Record<Exclude<DataSource, 'pipeline'>, string> = {
  mock: 'MOCK',
  stub: 'STUB',
  unknown: '?',
};

const TOOLTIP: Record<Exclude<DataSource, 'pipeline'>, string> = {
  mock: 'Backend returned seeded mock data — pipeline has no live data for this endpoint.',
  stub: 'WebSocket pushed a placeholder payload rather than real pipeline output.',
  unknown: 'Endpoint did not report a data source.',
};

export function MockBadge({ source, className }: MockBadgeProps) {
  if (source === undefined || source === 'pipeline') return null;
  return (
    <span
      title={TOOLTIP[source]}
      className={
        'ml-1.5 inline-flex h-4 items-center rounded px-1 font-mono text-[9px] font-bold uppercase tracking-wider ' +
        (source === 'unknown'
          ? 'bg-[var(--bg-surface-raised)] text-[var(--text-tertiary)]'
          : 'bg-[var(--trade-neutral-dim)] text-[var(--trade-neutral)]') +
        (className ? ` ${className}` : '')
      }
    >
      {LABEL[source]}
    </span>
  );
}
