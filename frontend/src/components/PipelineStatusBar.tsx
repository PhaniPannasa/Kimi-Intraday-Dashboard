import { usePipelineStatus } from '@/hooks/usePipelineStatus';
import { cn } from '@/lib/utils';

const layerOrder = [
  'l1_market_context',
  'l2_universe',
  'l3_signals',
  'l4_sector',
  'l5_scoring',
  'l6_ranking',
  'l7_confluence',
  'l8_thesis',
  'l9_monitor',
  'l10_edge',
];

const layerLabels: Record<string, string> = {
  l1_market_context: 'L1',
  l2_universe: 'L2',
  l3_signals: 'L3',
  l4_sector: 'L4',
  l5_scoring: 'L5',
  l6_ranking: 'L6',
  l7_confluence: 'L7',
  l8_thesis: 'L8',
  l9_monitor: 'L9',
  l10_edge: 'L10',
};

function LayerDot({
  name,
  status,
}: {
  name: string;
  status: { status: string; last_run: string | null; duration_ms: number } | undefined;
}) {
  const color =
    status?.status === 'ok'
      ? 'bg-[var(--trade-long)]'
      : status?.status === 'stale'
        ? 'bg-[var(--trade-neutral)]'
        : 'bg-[var(--trade-short)]';

  return (
    <div className="group relative flex items-center gap-1">
      <span className={cn('h-2 w-2 rounded-full', color)} />
      <span className="text-fluid-xs text-[var(--text-tertiary)]">{layerLabels[name]}</span>
      {status && (
        <div className="pointer-events-none absolute bottom-full left-1/2 mb-1 hidden -translate-x-1/2 whitespace-nowrap rounded bg-[var(--bg-surface-raised)] px-2 py-1 text-fluid-xs text-[var(--text-secondary)] shadow-lg group-hover:block">
          {layerLabels[name]} — {status.duration_ms}ms
        </div>
      )}
    </div>
  );
}

export function PipelineStatusBar() {
  const { data, isLoading } = usePipelineStatus();

  if (isLoading || !data) {
    return (
      <div className="flex h-8 items-center gap-2 border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 animate-pulse">
        <div className="h-4 w-32 rounded bg-[var(--bg-surface-raised)]" />
      </div>
    );
  }

  const anyStale = Object.values(data.layers).some((l) => l.status !== 'ok');

  return (
    <div
      className={cn(
        'flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-[var(--border-subtle)] px-3 py-1.5',
        anyStale ? 'bg-[var(--trade-neutral-dim)]/30' : 'bg-[var(--bg-surface)]'
      )}
    >
      <div className="flex items-center gap-1.5">
        {layerOrder.map((name) => (
          <LayerDot key={name} name={name} status={data.layers[name]} />
        ))}
      </div>
      <div className="ml-auto flex items-center gap-2 text-fluid-xs">
        <span className="text-[var(--text-secondary)]">
          {data.market_session} · {data.time_bucket}
        </span>
        <span className="text-[var(--text-tertiary)]">
          Cycle {data.cycle_duration_ms}ms
        </span>
      </div>
    </div>
  );
}
