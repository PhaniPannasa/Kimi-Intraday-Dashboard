'use client';

import { useMarketStore } from '@/stores/marketStore';
import { useHealth } from '@/hooks/useHealth';
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
  const wsConnected = useMarketStore((s) => s.wsConnected);
  const { data: health } = useHealth();

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

  const dbUp = health?.db_connected === true;
  const redisUp = health?.redis_connected === true;
  const tokenDays = health?.token_expires_in_days ?? 0;
  const feedState = health?.websocket ?? 'idle';
  const feedColor = feedState === 'connected'
    ? 'var(--trade-long)'
    : feedState === 'idle'
      ? 'var(--trade-neutral)'
      : 'var(--trade-short)';
  const schedulerJobs = health?.scheduler_jobs ?? 0;
  const items: HealthStripItem[] = [
    {
      label: 'Feed',
      value: feedState,
      color: feedColor,
    },
    {
      label: 'WS',
      value: wsConnected ? 'connected' : 'offline',
      color: wsConnected ? 'var(--trade-long)' : 'var(--trade-short)',
    },
    {
      label: 'DB',
      value: dbUp ? 'timescaledb' : 'down',
      color: dbUp ? 'var(--trade-long)' : 'var(--trade-short)',
    },
    {
      label: 'Cache',
      value: redisUp ? 'redis' : 'down',
      color: redisUp ? 'var(--trade-long)' : 'var(--trade-short)',
    },
    {
      label: 'Sched',
      value: schedulerJobs > 0 ? `${schedulerJobs} jobs` : 'idle',
      color:
        schedulerJobs > 0
          ? 'var(--trade-long)'
          : 'var(--trade-neutral)',
    },
    {
      label: 'Token',
      value: paused ? 'PAUSED' : (tokenDays > 0 ? `${tokenDays}d` : '—'),
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
