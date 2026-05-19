'use client';

import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import { useMarketStore } from '@/stores/marketStore';
import { MockBadge } from './MockBadge';
import type { ActivityEvent } from '@/types/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type CycleEventType =
  | 'NEW'
  | 'DROP'
  | 'TRIGGER'
  | 'T1'
  | 'ACTIVE'
  | 'INVALID'
  | 'JUMP_UP'
  | 'JUMP_DN'
  | 'STATE';

export interface CycleEvent {
  id: string;
  ts: number;
  type: CycleEventType;
  symbol: string;
  dir: 'LONG' | 'SHORT';
  text: string;
  detail: string;
  cycle: number;
}

// ---------------------------------------------------------------------------
// Visual config per event type
// ---------------------------------------------------------------------------

interface EventConfig {
  icon: string;
  color: string;
  label: string;
}

const EVENT_CONFIG: Record<CycleEventType, EventConfig> = {
  NEW:     { icon: '★', color: 'var(--accent)',         label: 'NEW' },
  DROP:    { icon: '↓', color: 'var(--text-tertiary)',  label: 'DROP' },
  TRIGGER: { icon: '▶', color: 'var(--accent)',         label: 'TRIG' },
  T1:      { icon: '⚑', color: 'var(--trade-long)',     label: 'T1' },
  ACTIVE:  { icon: '●', color: 'var(--trade-long)',     label: 'LIVE' },
  INVALID: { icon: '✕', color: 'var(--trade-short)',    label: 'STOP' },
  JUMP_UP: { icon: '▲', color: 'var(--trade-long)',     label: 'UP' },
  JUMP_DN: { icon: '▼', color: 'var(--trade-short)',    label: 'DOWN' },
  STATE:   { icon: '→', color: 'var(--text-secondary)', label: 'STATE' },
};

// Component: CycleActivity
// ---------------------------------------------------------------------------

export interface CycleActivityProps {
  events: (CycleEvent | ActivityEvent)[];
  onSelect: (symbol: string) => void;
  selectedSymbol: string | null;
}

// Helpers to normalise CycleEvent | ActivityEvent to a common shape
function eventTs(evt: CycleEvent | ActivityEvent): number {
  return typeof evt.ts === 'string' ? Date.parse(evt.ts) : evt.ts;
}
function eventDir(evt: CycleEvent | ActivityEvent): 'LONG' | 'SHORT' {
  return 'dir' in evt ? evt.dir : evt.direction;
}

export function CycleActivity({
  events,
  onSelect,
  selectedSymbol,
}: CycleActivityProps) {
  const source = useMarketStore((s) => s.sources['activity/events']);
  const totalEvents = events.length;
  const countNew = useMemo(() => events.filter((e) => e.type === 'NEW').length, [events]);
  const countT1 = useMemo(() => events.filter((e) => e.type === 'T1').length, [events]);
  const countTriggers = useMemo(
    () => events.filter((e) => e.type === 'TRIGGER').length,
    [events],
  );

  return (
    <div className="flex flex-col rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
      {/* ---- Header ---- */}
      <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-3 py-2">
        <h2 className="text-fluid-xs font-bold">Cycle Activity</h2>
        <MockBadge source={source} />
        <div className="flex items-center gap-1.5">
          {countNew > 0 && (
            <span
              className="rounded px-1.5 py-0.5 text-[9px] font-semibold"
              style={{
                backgroundColor: 'var(--accent-dim)',
                color: 'var(--accent)',
              }}
            >
              {countNew} new
            </span>
          )}
          {countTriggers > 0 && (
            <span
              className="rounded px-1.5 py-0.5 text-[9px] font-semibold"
              style={{
                backgroundColor: 'var(--accent-dim)',
                color: 'var(--accent)',
              }}
            >
              {countTriggers} trig
            </span>
          )}
          {countT1 > 0 && (
            <span
              className="rounded px-1.5 py-0.5 text-[9px] font-semibold"
              style={{
                backgroundColor: 'var(--trade-long-dim)',
                color: 'var(--trade-long)',
              }}
            >
              {countT1} T1
            </span>
          )}
          <span
            className="rounded bg-[var(--bg-surface-raised)] px-1.5 py-0.5 text-[9px] font-semibold text-[var(--text-secondary)]"
          >
            {totalEvents}
          </span>
        </div>
      </div>

      {/* ---- Event list ---- */}
      <div className="overflow-y-auto" style={{ maxHeight: 280 }}>
        {events.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-fluid-xs text-[var(--text-tertiary)]">
            No cycle activity yet
          </div>
        ) : (
          <div className="divide-y divide-[var(--border-subtle)]">
            {events.map((evt) => {
              const cfg = EVENT_CONFIG[evt.type];
              const isSelected = selectedSymbol === evt.symbol;
              const dir = eventDir(evt);
              const ts = eventTs(evt);
              return (
                <button
                  key={evt.id}
                  type="button"
                  onClick={() => onSelect(evt.symbol)}
                  className={cn(
                    'flex w-full items-start gap-2 px-3 py-1.5 text-left transition-colors',
                    'hover:bg-[var(--bg-surface-raised)]',
                    isSelected && 'bg-[var(--accent-dim)]',
                  )}
                >
                  {/* Timestamp */}
                  <span className="mt-0.5 shrink-0 font-mono text-[10px] tabular-nums text-[var(--text-tertiary)]">
                    {new Date(ts).toLocaleTimeString('en-IN', {
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                      hour12: false,
                    })}
                  </span>

                  {/* Type badge */}
                  <span
                    className="shrink-0 rounded px-1 py-0.5 text-[9px] font-bold uppercase tracking-wide"
                    style={{
                      backgroundColor: `color-mix(in srgb, ${cfg.color} 18%, transparent)`,
                      color: cfg.color,
                    }}
                  >
                    {cfg.icon} {cfg.label}
                  </span>

                  {/* Symbol + direction */}
                  <span
                    className={cn(
                      'shrink-0 text-fluid-xs font-bold',
                      dir === 'LONG'
                        ? 'text-[var(--trade-long)]'
                        : 'text-[var(--trade-short)]',
                    )}
                  >
                    {evt.symbol}
                  </span>

                  {/* Event text + detail */}
                  <div className="min-w-0 flex-1 leading-tight">
                    <div className="truncate text-fluid-xs text-[var(--text-primary)]">
                      {evt.text}
                    </div>
                    {evt.detail && (
                      <div className="truncate text-[10px] text-[var(--text-tertiary)]">
                        {evt.detail}
                      </div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
