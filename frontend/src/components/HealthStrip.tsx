'use client';

import { useMarketStore } from '@/stores/marketStore';
import { MockBadge } from './MockBadge';
import type { PipelineLayerStatus } from '@/types/api';

interface HealthStripItem {
  label: string;
  value: string | number;
  color: string;
}

interface HealthStripProps {
  pipeline: PipelineLayerStatus[];
  cycle: number;
  paused: boolean;
  lastCycleAt: number;
}

export function HealthStrip({
  pipeline,
  cycle,
  paused,
  lastCycleAt,
}: HealthStripProps) {
  const source = useMarketStore((s) => s.sources['pipeline/status']);

  if (!pipeline || pipeline.length === 0) {
    return (
      <div className="flex items-center gap-2 border-t border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-1.5">
        <span className="text-[10px] font-bold uppercase tracking-wide text-[var(--text-tertiary)]">
          Health
        </span>
        <MockBadge source={source} />
        <span className="flex-1" />
        <span className="text-[10px] italic text-[var(--text-tertiary)]">
          No cycles since startup
        </span>
      </div>
    );
  }

  const layersOk = pipeline.filter((l) => l.status === 'ok').length;
  const totalDuration = pipeline.reduce((sum, l) => sum + l.duration_ms, 0);

  const items: HealthStripItem[] = [
    { label: 'WS', value: 'connected', color: 'var(--trade-long)' },
    { label: 'DB', value: 'timescaledb', color: 'var(--trade-long)' },
    { label: 'Cache', value: 'redis', color: 'var(--trade-long)' },
    {
      label: 'Sched',
      value: `${layersOk}/${pipeline.length}`,
      color:
        layersOk === pipeline.length
          ? 'var(--trade-long)'
          : 'var(--trade-neutral)',
    },
    {
      label: 'Token',
      value: paused ? 'PAUSED' : '342d',
      color: paused ? 'var(--trade-neutral)' : 'var(--text-secondary)',
    },
    {
      label: 'Cycle',
      value: `${(totalDuration / 1000).toFixed(1)}s`,
      color: 'var(--text-secondary)',
    },
    {
      label: 'Last',
      value: lastCycleAt
        ? new Date(lastCycleAt).toLocaleTimeString('en-IN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
          })
        : '—',
      color: 'var(--text-secondary)',
    },
    {
      label: 'Cycle#',
      value: cycle,
      color: 'var(--text-secondary)',
    },
  ];

  return (
    <div
      className="flex items-center gap-3 overflow-x-auto border-t border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-1.5 text-[10px] no-scrollbar"
      style={{ whiteSpace: 'nowrap', paddingBottom: 'calc(0.375rem + env(safe-area-inset-bottom, 0px))' }}
    >
      <MockBadge source={source} />
      {items.map((it, i) => (
        <span key={it.label} className="flex items-center gap-1">
          {i > 0 && (
            <span className="text-[var(--text-faint)]">&middot;</span>
          )}
          <span className="text-[var(--text-tertiary)]">{it.label}</span>
          <span className="font-mono font-semibold" style={{ color: it.color }}>
            {it.value}
          </span>
        </span>
      ))}
    </div>
  );
}
