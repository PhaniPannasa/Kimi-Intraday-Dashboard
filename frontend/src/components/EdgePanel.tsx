import { useMarketStore } from '@/stores/marketStore';
import { cn } from '@/lib/utils';
import { DataAgeBadge } from './DataAgeBadge';
import { MockBadge } from './MockBadge';

const tierDescriptions: Record<number, string> = {
  1: 'Tier 1 — Full Confluence',
  2: 'Tier 2 — 5/6 Confluence',
  3: 'Tier 3 — Sector Aligned',
  4: 'Tier 4 — Regime Aligned',
  5: 'Tier 5 — Setup Valid',
  6: 'Tier 6 — Baseline',
};

export function EdgePanel() {
  const edgeTiers = useMarketStore((s) => s.edgeTiers);
  const ts = useMarketStore((s) => s.lastWSTimestamps['L10_EDGE']);
  const source = useMarketStore((s) => s.sources['edge/tiers'] ?? s.sources['ws/l10_edge']);
  const tierIds = Object.keys(edgeTiers)
    .map(Number)
    .sort((a, b) => a - b);

  return (
    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] flex flex-col max-h-[500px]">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-3 py-2 md:px-4 md:py-3">
        <h2 className="text-fluid-base font-bold">Edge Tiers</h2>
        <MockBadge source={source} />
        <DataAgeBadge timestamp={ts} />
        <span className="rounded bg-[var(--bg-surface-raised)] px-2 py-0.5 text-fluid-xs text-[var(--text-secondary)]">
          L10
        </span>
      </div>

      {/* Scrollable list */}
      <div className="flex-1 overflow-y-auto p-2 md:p-3 space-y-2">
        {tierIds.length === 0 ? (
          <div className="py-8 text-center text-fluid-sm text-[var(--text-secondary)]">
            No edge data — L10 needs at least 30 outcomes per tier
          </div>
        ) : (
          tierIds.map((id) => (
            <div
              key={id}
              className={cn(
                'rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/50 p-3',
                id <= 2 && 'border-[var(--trade-long)]/20'
              )}
            >
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    'flex h-6 w-6 items-center justify-center rounded-full text-fluid-xs font-bold',
                    id <= 2
                      ? 'bg-[var(--trade-long-dim)] text-[var(--trade-long)]'
                      : id <= 4
                        ? 'bg-[var(--trade-neutral-dim)] text-[var(--trade-neutral)]'
                        : 'bg-[var(--bg-surface-raised)] text-[var(--text-tertiary)]'
                  )}
                >
                  {id}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="text-fluid-sm font-medium">
                    {tierDescriptions[id] ?? `Tier ${id}`}
                  </div>
                  <div className="truncate text-fluid-xs text-[var(--text-secondary)]">
                    {edgeTiers[id]}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
