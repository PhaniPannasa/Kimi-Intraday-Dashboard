'use client';

import { useRef, useState, useEffect, useMemo } from 'react';
import { cn } from '@/lib/utils';
import { useMarketStore } from '@/stores/marketStore';
import { MockBadge } from './MockBadge';
import type { SimSnapshot, SimStock } from '@/data/engineSimulator';

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

const MAX_EVENTS = 60;

// ---------------------------------------------------------------------------
// Helper: build a Map<symbol, SimStock> from a snapshot
// ---------------------------------------------------------------------------

function buildStockMap(snapshot: SimSnapshot): Map<string, SimStock> {
  const map = new Map<string, SimStock>();
  for (const s of snapshot.universe.longs) map.set(s.symbol, s);
  for (const s of snapshot.universe.shorts) map.set(s.symbol, s);
  return map;
}

// ---------------------------------------------------------------------------
// Hook: useCycleActivity
// Tracks diffs between consecutive snapshots.  Returns events newest-first.
// ---------------------------------------------------------------------------

export function useCycleActivity(
  snapshot: SimSnapshot,
  cycle: number,
): CycleEvent[] {
  const [events, setEvents] = useState<CycleEvent[]>([]);
  const processedRef = useRef(-1);
  const prevRef = useRef<{
    stocks: Map<string, SimStock>;
    symbols: Set<string>;
  } | null>(null);

  useEffect(() => {
    if (cycle <= processedRef.current) return;
    processedRef.current = cycle;

    const currentStocks = buildStockMap(snapshot);
    const currentSymbols = new Set(currentStocks.keys());
    const now = Date.now();
    const newEvents: CycleEvent[] = [];

    if (cycle === 0) {
      // Seed: show "published as ATTRACTIVE" for the first batch
      const seedStocks = [...snapshot.universe.longs, ...snapshot.universe.shorts]
        .filter((s) => s.grade === 'ATTRACTIVE')
        .slice(0, 8);
      for (const s of seedStocks) {
        newEvents.push({
          id: `seed-${s.symbol}-${now}-${Math.random().toString(36).slice(2, 6)}`,
          ts: now - 60000 + Math.random() * 30000,
          type: 'NEW',
          symbol: s.symbol,
          dir: s.direction,
          text: 'Published as ATTRACTIVE',
          detail: `${s.setup_label} · Net R:R ${s.net_rr.toFixed(2)}`,
          cycle: 0,
        });
      }
    } else {
      const prev = prevRef.current;
      if (!prev) {
        // First real cycle with no previous data: just store and return
        prevRef.current = { stocks: currentStocks, symbols: currentSymbols };
        return;
      }

      // ---- NEW: symbols appearing in the top-25 for the first time ----
      for (const [sym, stock] of currentStocks) {
        if (!prev.symbols.has(sym)) {
          newEvents.push({
            id: `new-${sym}-${cycle}-${now}`,
            ts: now,
            type: 'NEW',
            symbol: sym,
            dir: stock.direction,
            text: 'New entrant in top 25',
            detail: `Score ${stock.score.toFixed(1)} · ${stock.setup_label}`,
            cycle,
          });
        }
      }

      // ---- DROP: symbols that fell out of the top-25 ----
      for (const sym of prev.symbols) {
        if (!currentSymbols.has(sym)) {
          const prevStock = prev.stocks.get(sym);
          newEvents.push({
            id: `drop-${sym}-${cycle}-${now}`,
            ts: now,
            type: 'DROP',
            symbol: sym,
            dir: prevStock?.direction ?? 'LONG',
            text: 'Dropped from top 25',
            detail: prevStock ? `Was score ${prevStock.score.toFixed(1)}` : '',
            cycle,
          });
        }
      }

      // ---- State transitions + score jumps (for symbols that persisted) ----
      for (const [sym, stock] of currentStocks) {
        const prevStock = prev.stocks.get(sym);
        if (!prevStock) continue;

        // --- State transitions ---
        if (prevStock.state !== stock.state) {
          if (prevStock.state === 'PENDING' && stock.state === 'TRIGGERED') {
            newEvents.push({
              id: `trig-${sym}-${cycle}-${now}`,
              ts: now,
              type: 'TRIGGER',
              symbol: sym,
              dir: stock.direction,
              text: `Triggered at ${stock.trigger.toFixed(1)}`,
              detail: `${stock.setup_label} · R:R ${stock.net_rr.toFixed(2)}`,
              cycle,
            });
          } else if (stock.state === 'T1_HIT') {
            newEvents.push({
              id: `t1-${sym}-${cycle}-${now}`,
              ts: now,
              type: 'T1',
              symbol: sym,
              dir: stock.direction,
              text: `T1 target hit at ${stock.t1.toFixed(1)}`,
              detail: `MFE +${stock.mfe_R.toFixed(2)}R · MAE ${stock.mae_R.toFixed(2)}R`,
              cycle,
            });
          } else if (stock.state === 'ACTIVE' && prevStock.state !== 'ACTIVE') {
            newEvents.push({
              id: `active-${sym}-${cycle}-${now}`,
              ts: now,
              type: 'ACTIVE',
              symbol: sym,
              dir: stock.direction,
              text: `Now active · MFE +${stock.mfe_R.toFixed(2)}R`,
              detail: `${stock.setup_label} @ ${stock.trigger.toFixed(1)}`,
              cycle,
            });
          } else {
            newEvents.push({
              id: `state-${sym}-${cycle}-${now}`,
              ts: now,
              type: 'STATE',
              symbol: sym,
              dir: stock.direction,
              text: `${prevStock.state} → ${stock.state}`,
              detail: `${stock.setup_label} · Score ${stock.score.toFixed(1)}`,
              cycle,
            });
          }
        }

        // --- Big score jumps (|Δ| >= 5) ---
        const diff = stock.score - prevStock.score;
        if (Math.abs(diff) >= 5) {
          newEvents.push({
            id: `jump-${sym}-${cycle}-${now}-${Math.random().toString(36).slice(2, 5)}`,
            ts: now,
            type: diff > 0 ? 'JUMP_UP' : 'JUMP_DN',
            symbol: sym,
            dir: stock.direction,
            text: `Score ${diff > 0 ? 'jumped' : 'dropped'} ${diff >= 0 ? '+' : ''}${diff.toFixed(1)}`,
            detail: `${prevStock.score.toFixed(1)} → ${stock.score.toFixed(1)}`,
            cycle,
          });
        }
      }
    }

    // Persist current state for the next cycle
    prevRef.current = { stocks: currentStocks, symbols: currentSymbols };

    // Accumulate (new events go to the front — newest first)
    if (newEvents.length > 0) {
      setEvents((prev) => [...newEvents.reverse(), ...prev].slice(0, MAX_EVENTS));
    }
  }, [snapshot, cycle]);

  return events;
}

// ---------------------------------------------------------------------------
// Component: CycleActivity
// ---------------------------------------------------------------------------

export interface CycleActivityProps {
  events: CycleEvent[];
  onSelect: (symbol: string) => void;
  selectedSymbol: string | null;
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
                    {new Date(evt.ts).toLocaleTimeString('en-IN', {
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
                      evt.dir === 'LONG'
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
