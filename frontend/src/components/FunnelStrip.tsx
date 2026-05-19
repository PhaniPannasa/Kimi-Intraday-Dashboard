'use client';

import { cn } from '@/lib/utils';
import { useMarketStore } from '@/stores/marketStore';
import { MockBadge } from './MockBadge';
import { LAYER_META } from '@/data/engineSimulator';
import type { SimPipelineLayer } from '@/data/engineSimulator';

const LAYER_ORDER = ['L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8', 'L9', 'L10'];

interface FunnelStripProps {
  layers: SimPipelineLayer[];
  activeLayer: number;
  funnel: Record<string, { in_count: number; out_count: number; layer: string }>;
  onInspect: (key: string) => void;
  inspectKey: string | null;
  learnMode: boolean;
}

export function FunnelStrip({
  layers,
  activeLayer,
  funnel,
  onInspect,
  inspectKey,
  learnMode,
}: FunnelStripProps) {
  const source = useMarketStore((s) => s.sources['funnel/counts']);
  const sourceCount = funnel?.L2?.in_count ?? 50;
  const promotedCount = funnel?.L10?.out_count ?? 0;
  const isEmpty = !funnel || Object.keys(funnel).length === 0;

  if (isEmpty) {
    return (
      <div className="flex items-center gap-2 border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2">
        <span className="text-[10px] font-bold uppercase tracking-wide text-[var(--text-tertiary)]">
          Funnel
        </span>
        <MockBadge source={source} />
        <span className="flex-1" />
        <span className="text-sm italic text-[var(--text-tertiary)]">
          Pipeline has not run a cycle
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]">
      {/* Horizontal strip */}
      <div className="flex items-stretch overflow-x-auto no-scrollbar">
        {/* Source label + MockBadge — left anchor */}
        <div className="flex shrink-0 flex-col justify-center border-r border-[var(--border-subtle)] px-3 py-2">
          <div className="flex items-center gap-1">
            <span className="text-[9px] font-medium uppercase tracking-wide text-[var(--text-tertiary)]">
              Source
            </span>
            <MockBadge source={source} />
          </div>
          <span className="font-mono text-sm font-bold tabular-nums text-[var(--text-primary)]">
            {sourceCount}
          </span>
          <span className="text-[9px] text-[var(--text-tertiary)]">Nifty 50</span>
        </div>

        {/* Layer tiles */}
        {layers.map((layer, i) => {
          const label = LAYER_ORDER[i] ?? layer.label;
          const meta = LAYER_META[label];
          const fd = funnel[label];
          const inCount = fd?.in_count ?? 0;
          const outCount = fd?.out_count ?? 0;
          const survPct = inCount > 0 ? (outCount / inCount) * 100 : 0;
          const dropPct = inCount > 0 ? ((inCount - outCount) / inCount) * 100 : 0;
          const isActive = i === activeLayer;
          const isInspected = inspectKey === label;
          const statusColor =
            layer.status === 'ok' ? 'var(--trade-long)' : 'var(--trade-short)';

          return (
            <button
              key={layer.key}
              onClick={() => onInspect(label)}
              className={cn(
                'group relative flex min-w-[72px] flex-col items-center justify-center px-2 py-1.5 text-center transition-all duration-200 sm:min-w-[88px] sm:px-3',
                isInspected && 'bg-[var(--bg-surface-raised)]',
              )}
              style={
                isInspected
                  ? { borderTop: '2px solid var(--accent)', background: 'var(--bg-surface-raised)' }
                  : undefined
              }
            >
              {/* Dot + label */}
              <div className="flex items-center gap-1.5">
                <span
                  className={cn('inline-block h-1.5 w-1.5 rounded-full', isActive && 'animate-layer-pulse')}
                  style={{ background: statusColor }}
                />
                <span className="text-[10px] font-bold tracking-wide text-[var(--text-secondary)]">
                  {label}
                </span>
              </div>

              {/* Layer name */}
              <span className="text-[9px] leading-tight text-[var(--text-tertiary)]">
                {meta?.name ?? layer.name}
              </span>

              {/* Duration */}
              <span className="mt-0.5 font-mono text-[8px] tabular-nums text-[var(--text-faint)]">
                {layer.duration_ms}ms
              </span>

              {/* Survivor count */}
              <span className="font-mono text-[10px] font-semibold tabular-nums text-[var(--text-secondary)]">
                {outCount}
              </span>

              {/* Mini funnel bar */}
              <div className="mt-0.5 h-[3px] w-full overflow-hidden rounded-full bg-[var(--bg-base)]">
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{
                    width: `${survPct}%`,
                    background:
                      survPct > 70
                        ? 'var(--trade-long)'
                        : survPct > 40
                          ? 'var(--trade-neutral)'
                          : 'var(--trade-short)',
                  }}
                />
              </div>

              {/* Drop percentage */}
              {dropPct > 5 && (
                <span className="text-[8px] text-[var(--text-tertiary)]">-{dropPct.toFixed(0)}%</span>
              )}

              {/* Separator */}
              {i < layers.length - 1 && (
                <div className="absolute right-0 top-1/2 h-[60%] w-px -translate-y-1/2 bg-[var(--border-subtle)]" />
              )}

              {/* Learn mode tooltip */}
              {learnMode && meta && (
                <div className="pointer-events-none absolute -bottom-8 left-1/2 z-20 hidden -translate-x-1/2 whitespace-nowrap rounded bg-[var(--bg-surface-elev)] px-2 py-1 text-[8px] text-[var(--text-secondary)] opacity-0 shadow-lg transition-opacity group-hover:opacity-100 sm:block">
                  {meta.purpose}
                </div>
              )}
            </button>
          );
        })}

        {/* Output label — right anchor */}
        <div className="flex shrink-0 flex-col justify-center border-l border-[var(--border-subtle)] px-3 py-2">
          <span className="text-[9px] font-medium uppercase tracking-wide text-[var(--text-tertiary)]">
            Output
          </span>
          <span className="font-mono text-sm font-bold tabular-nums text-[var(--trade-long)]">
            {promotedCount}
          </span>
          <span className="text-[9px] text-[var(--text-tertiary)]">Promoted</span>
        </div>
      </div>

      {/* Learn mode instruction bar */}
      {learnMode && (
        <div className="border-t border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/40 px-3 py-1.5 text-[9px] text-[var(--text-tertiary)]">
          <span className="font-semibold text-[var(--accent)]">LEARN</span> Click any layer tile to inspect
          its detailed view. The bar width shows survivor ratio vs input count.
        </div>
      )}
    </div>
  );
}
