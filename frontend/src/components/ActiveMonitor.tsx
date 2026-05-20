import { useMarketStore } from '@/stores/marketStore';
import { cn } from '@/lib/utils';
import { DataAgeBadge } from './DataAgeBadge';
import { MockBadge } from './MockBadge';
import { setupTypeLabels } from '@/types/api';

export function ActiveMonitor() {
  const theses = useMarketStore((s) => s.theses);
  const activeTheses = useMarketStore((s) => s.activeTheses);
  const invalidated = useMarketStore((s) => s.invalidatedTheses);
  const setSelectedThesis = useMarketStore((s) => s.setSelectedThesis);
  const ts = useMarketStore((s) => s.lastWSTimestamps['L8_THESIS']);
  const source = useMarketStore((s) => s.sources['monitor/active-theses'] ?? s.sources['ws/l8_thesis']);

  // Build a unified display list. Prefer REST (ActiveThesisEntry) when
  // present; otherwise fall back to WS-pushed ThesisCard data so the panel
  // still works when only one source is populated.
  type DisplayRow = {
    thesis_id: string;
    symbol: string;
    direction: 'LONG' | 'SHORT';
    badge: string; // grade (ThesisCard) or state (ActiveThesisEntry)
    setup_label: string;
    net_rr: number;
    trigger: number;
  };

  const rows: DisplayRow[] = activeTheses.length > 0
    ? activeTheses.map((t) => ({
        thesis_id: t.thesis_id,
        symbol: t.symbol,
        direction: t.direction,
        badge: t.state,
        setup_label: t.setup_label,
        net_rr: t.net_rr,
        trigger: t.trigger,
      }))
    : theses.map((t) => ({
        thesis_id: t.thesis_id,
        symbol: t.symbol,
        direction: t.direction,
        badge: t.grade,
        setup_label: setupTypeLabels[t.setup_type] ?? String(t.setup_type),
        net_rr: t.net_rr,
        trigger: t.trigger,
      }));

  // Click selects the matching ThesisCard from s.theses if one exists
  // (so DetailPanel still gets a fully-typed ThesisCard).
  const handleSelect = (row: DisplayRow) => {
    const match = theses.find(
      (t) => t.thesis_id === row.thesis_id ||
        (t.symbol === row.symbol && t.direction === row.direction)
    );
    if (match) setSelectedThesis(match);
  };

  return (
    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] flex flex-col max-h-[500px]"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-3 py-2 md:px-4 md:py-3"
      >
        <h2 className="text-fluid-base font-bold"
        >Live Theses
        </h2>
        <MockBadge source={source} />
        <DataAgeBadge timestamp={ts} />
        <span className="rounded bg-[var(--bg-surface-raised)] px-2 py-0.5 text-fluid-xs text-[var(--text-secondary)]"
        >
          {rows.length} active
        </span>
      </div>

      {/* Scrollable list */}
      <div className="flex-1 overflow-y-auto p-2 md:p-3 space-y-2"
      >
        {rows.length === 0 ? (
          <div className="py-8 text-center text-fluid-sm text-[var(--text-secondary)]"
          >
            No active theses
          </div>
        ) : (
          rows.map((t) => (
            <button
              key={t.thesis_id}
              onClick={() => handleSelect(t)}
              className={cn(
                'w-full rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/50 p-2 text-left transition-colors',
                'hover:border-[var(--border-subtle)]/80 hover:bg-[var(--bg-surface-raised)]'
              )}
            >
              <div className="flex items-center justify-between"
              >
                <div className="flex items-center gap-2"
                >
                  <span
                    className={cn(
                      'h-1.5 w-1.5 rounded-full',
                      t.direction === 'LONG' ? 'bg-[var(--trade-long)]' : 'bg-[var(--trade-short)]'
                    )}
                  />
                  <span className="text-fluid-sm font-bold"
                  >{t.symbol}
                  </span>
                  <span className={cn(
                    'text-fluid-xs',
                    t.direction === 'LONG' ? 'text-[var(--trade-long)]' : 'text-[var(--trade-short)]'
                  )}
                  >
                    {t.direction}
                  </span>
                </div>
                <span
                  className={cn(
                    'text-fluid-xs font-bold',
                    t.badge === 'ATTRACTIVE'
                      ? 'text-[var(--trade-long)]'
                      : t.badge === 'MARGINAL'
                        ? 'text-[var(--trade-neutral)]'
                        : 'text-[var(--trade-short)]'
                  )}
                >
                  {t.badge}
                </span>
              </div>
              <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-fluid-xs text-[var(--text-secondary)]"
              >
                <span
                >{t.setup_label}
                </span>
                <span className="tabular-nums"
                >R:R {t.net_rr.toFixed(2)}
                </span>
                <span className="tabular-nums"
                >Tr {t.trigger.toFixed(1)}
                </span>
              </div>
            </button>
          ))
        )}

        {/* Recently invalidated */}
        {invalidated.length > 0 && (
          <>
            <div className="my-2 h-px bg-[var(--border-subtle)]"
            />
            <div className="px-1 text-fluid-xs font-medium text-[var(--text-tertiary)]"
            >
              Recently Invalidated ({invalidated.length})
            </div>
            {invalidated.slice(-5).reverse().map((inv) => (
              <div
                key={inv.thesis_id + inv.timestamp}
                className="rounded-md border border-[var(--trade-short)]/10 bg-[var(--trade-short-dim)]/20 p-2"
              >
                <div className="flex items-center justify-between"
                >
                  <span className="text-fluid-sm font-medium text-[var(--trade-short)]"
                  >{inv.thesis_id}
                  </span>
                  <span className="text-fluid-xs text-[var(--text-tertiary)]"
                  >
                    {new Date(inv.timestamp).toLocaleTimeString('en-IN', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
                <div className="mt-0.5 text-fluid-xs text-[var(--text-secondary)]"
                >{inv.reason}
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
