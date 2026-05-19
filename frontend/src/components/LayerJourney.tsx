'use client';

import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import { evaluateLayers, LAYER_META } from '@/data/simTypes';
import { VerdictPill } from './SharedComponents';
import type { SimStock, SimMarketContext } from '@/data/simTypes';

interface LayerJourneyProps {
  entry: SimStock | null;
  ctx: SimMarketContext;
  learnMode: boolean;
  activeLayer: number;
}

const LAYER_ORDER = ['L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8', 'L9', 'L10'] as const;

/* ─── Pip row — 10 colored dots ─────────────────────── */
function StatusPips({ layers }: { layers: ReturnType<typeof evaluateLayers> }) {
  return (
    <div className="flex items-center gap-1">
      {LAYER_ORDER.map((key) => {
        const v = layers[key as keyof typeof layers].verdict;
        const color =
          v === 'PASS'
            ? 'var(--trade-long)'
            : v === 'WARN'
              ? 'var(--trade-neutral)'
              : v === 'FAIL'
                ? 'var(--trade-short)'
                : v === 'LIVE'
                  ? 'var(--accent)'
                  : 'var(--text-faint)';
        return (
          <span
            key={key}
            className="inline-block h-2 w-2 rounded-full"
            style={{ background: color, boxShadow: `0 0 4px ${color}` }}
            title={`${key}: ${v}`}
          />
        );
      })}
    </div>
  );
}

/* ─── L5 mini factor bars ───────────────────────────── */
function FactorBars({
  factors,
}: {
  factors: { label: string; v: number }[];
}) {
  return (
    <div className="mt-2 space-y-1">
      {factors.map((f) => {
        const pct = Math.min(100, f.v);
        const color =
          pct >= 70 ? 'var(--trade-long)' : pct >= 40 ? 'var(--trade-neutral)' : 'var(--trade-short)';
        return (
          <div key={f.label} className="flex items-center gap-2">
            <span className="w-14 shrink-0 text-[9px] text-[var(--text-tertiary)]">{f.label}</span>
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[var(--bg-base)]">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${pct}%`, background: color }}
              />
            </div>
            <span className="w-6 text-right font-mono text-[10px] tabular-nums text-[var(--text-secondary)]">
              {f.v}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/* ─── L7 confluence check grid ──────────────────────── */
function ConfluenceGrid({
  checks,
}: {
  checks: { label: string; ok: boolean }[];
}) {
  return (
    <div className="mt-2 grid grid-cols-3 gap-1">
      {checks.map((c) => (
        <span
          key={c.label}
          className={cn(
            'inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[9px] font-medium',
            c.ok
              ? 'bg-[var(--trade-long-dim)] text-[var(--trade-long)]'
              : 'bg-[var(--trade-short-dim)] text-[var(--trade-short)]',
          )}
        >
          <span className="font-bold">{c.ok ? '✓' : '✗'}</span>
          <span className="truncate">{c.label}</span>
        </span>
      ))}
    </div>
  );
}

/* ─── L8 levels mini-grid ───────────────────────────── */
function LevelsGrid({
  levels,
}: {
  levels: {
    trigger: number;
    invalidation: number;
    t1: number;
    t2: number;
    gross_rr: number;
    net_rr: number;
    decay: number;
    tier: string;
    grade: string;
    setup: string;
  };
}) {
  return (
    <div className="mt-2 grid grid-cols-4 gap-1.5">
      <div className="rounded border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/30 p-1.5 text-center">
        <div className="text-[8px] text-[var(--text-tertiary)]">Trigger</div>
        <div className="font-mono text-[11px] font-bold tabular-nums text-[var(--trade-long)]">
          {levels.trigger.toFixed(1)}
        </div>
      </div>
      <div className="rounded border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/30 p-1.5 text-center">
        <div className="text-[8px] text-[var(--text-tertiary)]">Invalid</div>
        <div className="font-mono text-[11px] font-bold tabular-nums text-[var(--trade-short)]">
          {levels.invalidation.toFixed(1)}
        </div>
      </div>
      <div className="rounded border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/30 p-1.5 text-center">
        <div className="text-[8px] text-[var(--text-tertiary)]">T1</div>
        <div className="font-mono text-[11px] font-bold tabular-nums text-[var(--trade-neutral)]">
          {levels.t1.toFixed(1)}
        </div>
      </div>
      <div className="rounded border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/30 p-1.5 text-center">
        <div className="text-[8px] text-[var(--text-tertiary)]">T2</div>
        <div className="font-mono text-[11px] font-bold tabular-nums text-[var(--text-primary)]">
          {levels.t2.toFixed(1)}
        </div>
      </div>
      <div className="col-span-2 flex items-center justify-center gap-2 rounded border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/30 p-1">
        <span className="text-[9px] text-[var(--text-tertiary)]">Net R:R</span>
        <span className="font-mono text-[11px] font-bold tabular-nums" style={{
          color: levels.net_rr >= 1.5 ? 'var(--trade-long)' : levels.net_rr >= 1 ? 'var(--trade-neutral)' : 'var(--trade-short)',
        }}>
          {levels.net_rr.toFixed(2)}
        </span>
      </div>
      <div className="col-span-2 flex items-center justify-center gap-2 rounded border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/30 p-1">
        <span className="text-[9px] text-[var(--text-tertiary)]">Decay</span>
        <span className="font-mono text-[11px] font-bold tabular-nums text-[var(--text-secondary)]">
          {levels.decay.toFixed(2)}
        </span>
      </div>
    </div>
  );
}

/* ─── L9 state pipeline ─────────────────────────────── */
function StatePipeline({ state }: { state: string }) {
  const stages = ['PENDING', 'TRIGGERED', 'ACTIVE', 'T1_HIT', 'STOPPED_OUT'];
  const idx = stages.indexOf(state);

  return (
    <div className="mt-2 flex items-center gap-0.5 overflow-x-auto">
      {stages.map((s, i) => {
        const isPast = idx > i;
        const isCurrent = idx === i;
        const isFail = s === 'STOPPED_OUT' && isCurrent;
        const color = isFail
          ? 'var(--trade-short)'
          : isCurrent
            ? 'var(--accent)'
            : isPast
              ? 'var(--trade-long)'
              : 'var(--text-faint)';
        return (
          <div key={s} className="flex items-center gap-0.5">
            <span
              className={cn(
                'inline-flex items-center rounded px-1.5 py-0.5 text-[8px] font-bold tracking-wide',
                isCurrent && 'animate-layer-pulse',
              )}
              style={{
                color,
                background: isCurrent || isPast ? `${color}22` : 'transparent',
                border: `1px solid ${color}44`,
              }}
            >
              {s === 'STOPPED_OUT' ? 'STOP' : s.replace('_HIT', '')}
            </span>
            {i < stages.length - 1 && (
              <span className="text-[8px]" style={{ color: isPast ? 'var(--trade-long)' : 'var(--text-faint)' }}>
                →
              </span>
            )}
          </div>
        );
      })}
      {state && !stages.includes(state) && (
        <span className="ml-1 rounded bg-[var(--accent-dim)] px-1 py-0.5 text-[8px] font-bold text-[var(--accent)]">
          {state}
        </span>
      )}
    </div>
  );
}

/* ─── L10 edge hit-rate bar ─────────────────────────── */
function EdgeBar({
  edge,
}: {
  edge: { tier: number; hit: number; ci_lo: number; ci_hi: number; n: number; setup: string; regime: string };
}) {
  const hitPct = (edge.hit * 100).toFixed(0);
  const loPct = (edge.ci_lo * 100).toFixed(0);
  const hiPct = (edge.ci_hi * 100).toFixed(0);

  return (
    <div className="mt-2 space-y-1">
      <div className="flex items-center gap-3">
        <span className="text-[10px] text-[var(--text-tertiary)]">Hit Rate</span>
        <span className="font-mono text-sm font-bold tabular-nums text-[var(--trade-long)]">
          {hitPct}%
        </span>
        <span className="text-[9px] text-[var(--text-tertiary)]">
          CI: [{loPct}–{hiPct}]
        </span>
        <span className="font-mono text-[9px] text-[var(--text-faint)]">N={edge.n}</span>
      </div>
      <div className="relative h-3 w-full">
        {/* CI range bar */}
        <div
          className="absolute top-0 h-3 rounded-full"
          style={{
            left: `${edge.ci_lo * 100}%`,
            right: `${100 - edge.ci_hi * 100}%`,
            background: 'var(--accent-dim)',
            border: '1px solid var(--accent-soft)',
          }}
        />
        {/* Hit rate dot */}
        <div
          className="absolute top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{
            left: `${edge.hit * 100}%`,
            background: 'var(--trade-long)',
            boxShadow: '0 0 6px var(--trade-long-soft)',
          }}
        />
        {/* Scale ticks */}
        <div className="flex w-full justify-between text-[7px] text-[var(--text-faint)]" style={{ marginTop: '14px' }}>
          <span>0%</span>
          <span>25%</span>
          <span>50%</span>
          <span>75%</span>
          <span>100%</span>
        </div>
      </div>
    </div>
  );
}

/* ─── Layer station ──────────────────────────────────── */
function Station({
  layerKey,
  index,
  data,
  learnMode,
  isActive,
}: {
  layerKey: string;
  index: number;
  data: ReturnType<typeof evaluateLayers>[keyof ReturnType<typeof evaluateLayers>];
  learnMode: boolean;
  isActive?: boolean;
}) {
  const meta = LAYER_META[layerKey];

  return (
    <div className="group relative flex gap-3">
      {/* Rail + node */}
      <div className="flex flex-col items-center">
        {/* Rail line above node */}
        <div className="h-0 w-0.5 bg-[var(--border-subtle)]" />
        {/* Node */}
        <div
          className={cn(
            'z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 text-[11px] font-bold transition-colors',
            isActive && 'animate-layer-pulse',
            data.verdict === 'PASS'
              ? 'border-[var(--trade-long)] bg-[var(--trade-long-dim)] text-[var(--trade-long)]'
              : data.verdict === 'WARN'
                ? 'border-[var(--trade-neutral)] bg-[var(--trade-neutral-dim)] text-[var(--trade-neutral)]'
                : data.verdict === 'FAIL'
                  ? 'border-[var(--trade-short)] bg-[var(--trade-short-dim)] text-[var(--trade-short)]'
                  : data.verdict === 'LIVE'
                    ? 'border-[var(--accent)] bg-[var(--accent-dim)] text-[var(--accent)]'
                    : 'border-[var(--text-faint)] bg-[var(--bg-surface-raised)] text-[var(--text-faint)]',
          )}
          style={isActive ? { boxShadow: '0 0 12px var(--accent-soft)' } : undefined}
        >
          {index + 1}
        </div>
        {/* Rail line below node */}
        {index < 9 && <div className="flex-1 w-0.5 bg-[var(--border-subtle)]" />}
      </div>

      {/* Content card */}
      <div className="mb-4 min-w-0 flex-1 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/30 p-3 transition-colors hover:border-[var(--border-strong)]">
        {/* Header row */}
        <div className="mb-1 flex items-center gap-2">
          <span className="text-[11px] font-bold text-[var(--text-primary)]">
            {layerKey} {meta?.name ?? ''}
          </span>
          <VerdictPill verdict={data.verdict} />
          {learnMode && (
            <span className="ml-auto rounded bg-[var(--accent-dim)] px-1 py-0.5 text-[8px] font-bold text-[var(--accent)]">
              LEARN
            </span>
          )}
        </div>

        {/* Headline */}
        <div className="text-[11px] font-medium text-[var(--text-secondary)]">{data.headline}</div>

        {/* Reason */}
        <div className="text-[10px] text-[var(--text-tertiary)]">{data.reason}</div>

        {/* Layer-specific extras */}
        {layerKey === 'L5' && 'factors' in data && data.factors && (
          <FactorBars factors={data.factors} />
        )}

        {layerKey === 'L7' && 'checkRows' in data && data.checkRows && (
          <ConfluenceGrid checks={data.checkRows} />
        )}

        {layerKey === 'L8' && 'levels' in data && data.levels && (
          <LevelsGrid levels={data.levels} />
        )}

        {layerKey === 'L9' && 'state' in data && data.state && (
          <StatePipeline state={data.state} />
        )}

        {layerKey === 'L10' && 'edge' in data && data.edge && (
          <EdgeBar edge={data.edge} />
        )}

        {/* Learn mode caption */}
        {learnMode && meta && (
          <div className="mt-2 rounded border border-[var(--accent-dim)]/30 bg-[var(--accent-dim)]/10 px-2 py-1 text-[9px] italic text-[var(--text-tertiary)]">
            {meta.purpose}
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Main component ────────────────────────────────── */
export function LayerJourney({ entry, ctx, learnMode, activeLayer }: LayerJourneyProps) {
  const layers = useMemo(() => {
    if (!entry) return null;
    return evaluateLayers(entry, ctx);
  }, [entry, ctx]);

  if (!entry || !layers) {
    return (
      <div className="flex h-48 items-center justify-center rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
        <div className="text-center">
          <div className="text-[13px] font-medium text-[var(--text-secondary)]">
            No Stock Selected
          </div>
          <div className="mt-1 text-[11px] text-[var(--text-tertiary)]">
            Click a row in the Top 25 table to see its layer-by-layer audit trail
          </div>
        </div>
      </div>
    );
  }

  const isLong = entry.direction === 'LONG';

  return (
    <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
      {/* Synthesis card */}
      <div className="border-b border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/40 p-3">
        <div className="mb-2 flex items-center gap-2">
          <span
            className="text-sm font-bold"
            style={{
              color: isLong ? 'var(--trade-long)' : 'var(--trade-short)',
            }}
          >
            {entry.symbol}
          </span>
          <span
            className={cn(
              'rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide',
              isLong
                ? 'bg-[var(--trade-long-dim)] text-[var(--trade-long)]'
                : 'bg-[var(--trade-short-dim)] text-[var(--trade-short)]',
            )}
          >
            {entry.direction}
          </span>
          <StatusPips layers={layers} />
          <span className="ml-auto text-[10px] text-[var(--text-tertiary)]">
            {entry.sector_name} · Price {entry.price.toFixed(1)}
          </span>
        </div>
        <div className="text-[11px] text-[var(--text-secondary)]">
          {isLong ? 'Bullish' : 'Bearish'} thesis via {entry.setup_label} ·{' '}
          {entry.confluence_score}/6 confluence · Composite{' '}
          <span className="font-mono font-bold">{entry.score.toFixed(1)}</span> · Net R:R{' '}
          <span className="font-mono font-bold">{entry.net_rr.toFixed(2)}</span> ·{' '}
          <span
            className="font-semibold"
            style={{
              color:
                entry.grade === 'ATTRACTIVE'
                  ? 'var(--trade-long)'
                  : entry.grade === 'MARGINAL'
                    ? 'var(--trade-neutral)'
                    : 'var(--text-tertiary)',
            }}
          >
            {entry.grade}
          </span>
        </div>
      </div>

      {/* Timeline */}
      <div className="overflow-y-auto px-3 pt-2" style={{ maxHeight: '70vh' }}>
        {LAYER_ORDER.map((key, i) => {
          const data = layers[key as keyof typeof layers];
          return (
            <Station
              key={key}
              layerKey={key}
              index={i}
              data={data}
              learnMode={learnMode}
              isActive={i === activeLayer}
            />
          );
        })}
      </div>
    </div>
  );
}
