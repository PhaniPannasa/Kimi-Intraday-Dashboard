import { usePipelineStatus } from '@/hooks/usePipelineStatus';
import { cn } from '@/lib/utils';

const layerInfo = [
  { key: 'l1_market_context', label: 'L1', name: 'Market Context' },
  { key: 'l2_universe', label: 'L2', name: 'Universe' },
  { key: 'l3_signals', label: 'L3', name: 'Signals' },
  { key: 'l4_sector', label: 'L4', name: 'Sector' },
  { key: 'l5_scoring', label: 'L5', name: 'Scoring' },
  { key: 'l6_ranking', label: 'L6', name: 'Ranking' },
  { key: 'l7_confluence', label: 'L7', name: 'Confluence' },
  { key: 'l8_thesis', label: 'L8', name: 'Thesis' },
  { key: 'l9_monitor', label: 'L9', name: 'Monitor' },
  { key: 'l10_edge', label: 'L10', name: 'Edge' },
];

interface PipelineStatusBarProps {
  activeLayer?: number; // 0-9 index, -1 means idle
}

export function PipelineStatusBar({ activeLayer = -1 }: PipelineStatusBarProps) {
  const { data, isLoading } = usePipelineStatus();

  if (isLoading || !data) {
    return (
      <div className="flex h-10 items-center gap-2 border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3">
        <div className="h-4 w-64 animate-pulse rounded bg-[var(--bg-surface-raised)]" />
      </div>
    );
  }

  const totalDuration = Object.values(data.layers).reduce(
    (sum, l) => sum + (l?.duration_ms ?? 0),
    0
  );

  return (
    <div
      className="flex items-stretch overflow-x-auto border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] py-0 no-scrollbar"
    >
      {layerInfo.map((layer, i) => {
        const status = data.layers[layer.key];
        const running = i === activeLayer;
        const done = activeLayer === -1 || i < activeLayer;
        const color =
          status?.status === 'ok'
            ? 'var(--trade-long)'
            : status?.status === 'stale'
              ? 'var(--trade-neutral)'
              : 'var(--trade-short)';

        return (
          <div
            key={layer.key}
            className="relative flex min-w-[64px] flex-col justify-center px-2 py-2 transition-colors sm:min-w-[84px] sm:px-3"
            style={{
              background: running ? 'var(--bg-surface-raised)' : 'transparent',
            }}
          >
            <div className="flex items-center gap-1.5">
              <span
                className={cn(
                  'inline-block h-1.5 w-1.5 rounded-full',
                  running && 'animate-layer-pulse'
                )}
                style={{
                  background: color,
                  opacity: done || running ? 1 : 0.35,
                }}
              />
              <span className="text-[10px] font-bold text-[var(--text-secondary)] tracking-wide">
                {layer.label}
              </span>
              <span className="ml-auto hidden text-[9px] text-[var(--text-tertiary)] sm:block">
                {status?.duration_ms ?? 0}ms
              </span>
            </div>
            <span className="hidden text-[9px] text-[var(--text-tertiary)] sm:block">
              {layer.name}
            </span>
            {/* Connector line */}
            {i < layerInfo.length - 1 && (
              <div className="absolute right-0 top-1/2 h-[60%] w-px -translate-y-1/2 bg-[var(--border-subtle)]" />
            )}
          </div>
        );
      })}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Right side info */}
      <div className="flex items-center gap-3 border-l border-[var(--border-subtle)] px-3 text-[10px] text-[var(--text-tertiary)]">
        <span>
          cycle{' '}
          <span className="font-mono text-[var(--text-secondary)]">{totalDuration}ms</span>
        </span>
        <span className="hidden sm:inline">· 100 symbols / minute</span>
      </div>
    </div>
  );
}