'use client';

import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import { LAYER_META, setupTypeLabels } from '@/types/api';
import type { SymbolFactorBreakdown, MarketContextFrame } from '@/types/api';
import { VerdictPill } from './SharedComponents';

interface LayerJourneyProps {
  entry: SymbolFactorBreakdown | null;
  ctx: MarketContextFrame;
  learnMode: boolean;
  activeLayer: number;
}

const LAYER_ORDER = ['L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8', 'L9', 'L10'] as const;

// ─── evaluateLayers (moved from simTypes.ts) ───────────────────────

function evaluateLayers(entry: SymbolFactorBreakdown, ctx: MarketContextFrame) {
  const isLong = entry.direction === 'LONG';
  const dirAligned =
    (isLong && ctx.regime === 'Trending-Up') ||
    (!isLong && ctx.regime === 'Trending-Down') ||
    ctx.regime === 'Range-Bound';

  return {
    L1: {
      verdict: dirAligned ? 'PASS' : 'WARN',
      headline: `${ctx.regime} · VIX ${ctx.vix_value.toFixed(1)} ${ctx.vix_band}`,
      reason: dirAligned
        ? `Regime supports ${entry.direction.toLowerCase()} setups`
        : `${entry.direction} bias fighting ${ctx.regime} regime`,
      chips: [
        {
          label: ctx.regime,
          kind:
            ctx.regime === 'Trending-Up'
              ? 'long'
              : ctx.regime === 'Trending-Down'
                ? 'short'
                : 'neutral',
        },
      ],
    },
    L2: {
      verdict: entry.l2_universe.fo_ban
        ? 'FAIL'
        : entry.l2_universe.lqs_score < 0.7 || entry.l2_universe.earnings_flag !== 'None'
          ? 'WARN'
          : 'PASS',
      headline: `LQS ${(entry.l2_universe.lqs_score * 100).toFixed(0)} (${entry.l2_universe.liquidity_quality})`,
      reason: entry.l2_universe.fo_ban
        ? 'BANNED — F&O ban-list'
        : 'Passed liquidity & eligibility gates',
    },
    L3: {
      verdict: entry.l3_signals.ema_aligned ? 'PASS' : 'WARN',
      headline: `EMA ${entry.l3_signals.ema_aligned ? 'aligned' : 'mixed'} · RSI ${entry.l3_signals.rsi.toFixed(0)} · ADX ${entry.l3_signals.adx.toFixed(0)}`,
      reason: entry.l3_signals.ema_aligned
        ? `Full ${isLong ? 'bullish' : 'bearish'} signal stack`
        : 'Signals mixed',
      factors: [
        { label: 'Trend', v: entry.l5_scores.f1_trend },
        { label: 'Momentum', v: entry.l5_scores.f2_momentum },
        { label: 'Volume', v: entry.l5_scores.f3_volume },
        { label: 'Vol-Pos', v: entry.l5_scores.f4_volpos },
        { label: 'Structure', v: entry.l5_scores.f5_structure },
        { label: 'Sector', v: entry.l5_scores.f6_sector },
        { label: 'Risk', v: entry.l5_scores.f7_risk },
      ],
    },
    L4: {
      verdict:
        entry.l4_sector.rs_ratio > 1.02 && entry.l4_sector.rs_momentum > 1
          ? 'PASS'
          : entry.l4_sector.rs_ratio < 0.98
            ? 'FAIL'
            : 'WARN',
      headline: `${entry.l4_sector.sector_name} #${entry.l4_sector.rotation_rank} · RS-Ratio ${entry.l4_sector.rs_ratio.toFixed(3)}`,
      reason:
        entry.l4_sector.rs_ratio > 1.02
          ? `${entry.l4_sector.sector_name} outperforming`
          : `${entry.l4_sector.sector_name} in line`,
    },
    L5: {
      verdict: entry.l5_scores.total >= 75 ? 'PASS' : entry.l5_scores.total >= 60 ? 'WARN' : 'FAIL',
      headline: `Composite ${entry.l5_scores.total.toFixed(1)}`,
      reason: entry.l5_scores.total >= 75 ? 'Multi-factor confirmation' : 'Mid-tier score',
    },
    L6: {
      verdict:
        entry.l6_ranking.rank_movement === 'UP' || entry.l6_ranking.rank_movement === 'NEW'
          ? 'PASS'
          : entry.l6_ranking.rank_movement === 'DOWN'
            ? 'WARN'
            : 'PASS',
      headline: `Δ ${entry.l6_ranking.score_change >= 0 ? '+' : ''}${entry.l6_ranking.score_change.toFixed(2)} · ${entry.l6_ranking.rank_movement}`,
      reason:
        entry.l6_ranking.rank_movement === 'NEW'
          ? 'New entrant this cycle'
          : entry.l6_ranking.rank_movement === 'UP'
            ? 'Rising in rank'
            : 'Steady',
    },
    L7: {
      verdict:
        entry.l7_confluence.score >= 5
          ? 'PASS'
          : entry.l7_confluence.score >= 3
            ? 'WARN'
            : 'FAIL',
      headline: `${entry.l7_confluence.score}/6 confluence checks passed`,
      reason: entry.l7_confluence.score >= 5 ? 'High-quality confluence' : 'Partial confluence',
      checkRows: Object.entries(entry.l7_confluence.checks).map(
        ([label, ok]: [string, boolean]) => ({
          label: label
            .replace(/_/g, ' ')
            .replace(/\b\w/g, (c: string) => c.toUpperCase()),
          ok,
        }),
      ),
    },
    L8: {
      verdict:
        entry.l8_thesis.grade === 'ATTRACTIVE'
          ? 'PASS'
          : entry.l8_thesis.grade === 'MARGINAL'
            ? 'WARN'
            : 'FAIL',
      headline: `${setupTypeLabels[entry.l8_thesis.setup_type] ?? entry.l8_thesis.setup_type} · Net R:R ${entry.l8_thesis.net_rr.toFixed(2)}`,
      reason:
        entry.l8_thesis.grade === 'ATTRACTIVE'
          ? 'Thesis published as Tradeable'
          : 'R:R below threshold',
      levels: {
        trigger: entry.l8_thesis.trigger,
        invalidation: entry.l8_thesis.invalidation,
        t1: entry.l8_thesis.t1,
        t2: entry.l8_thesis.t2,
        gross_rr: entry.l8_thesis.gross_rr,
        net_rr: entry.l8_thesis.net_rr,
        decay: 1.0,
        tier: entry.l8_thesis.actionability_tier,
        grade: entry.l8_thesis.grade,
        setup: setupTypeLabels[entry.l8_thesis.setup_type] ?? entry.l8_thesis.setup_type.toString(),
      },
    },
    L9: {
      verdict:
        !entry.l9_monitor || entry.l9_monitor.state === 'PENDING'
          ? 'NA'
          : entry.l9_monitor.state === 'ACTIVE' ||
              entry.l9_monitor.state === 'T1_HIT' ||
              entry.l9_monitor.state === 'TRIGGERED'
            ? 'LIVE'
            : 'WARN',
      headline: `State ${entry.l9_monitor?.state ?? 'PENDING'} · MFE +${(entry.l9_monitor?.mfe_R ?? 0).toFixed(2)}R`,
      reason:
        entry.l9_monitor?.state === 'PENDING' || !entry.l9_monitor
          ? `Waiting for trigger`
          : 'Live in shadow ledger',
      state: entry.l9_monitor?.state ?? 'PENDING',
    },
    L10: {
      verdict:
        (entry.l10_edge?.edge_tier ?? 6) <= 2
          ? 'PASS'
          : (entry.l10_edge?.edge_tier ?? 6) <= 4
            ? 'WARN'
            : 'NA',
      headline: `T${entry.l10_edge?.edge_tier ?? 6} · hit rate ${((0.42 + (7 - (entry.l10_edge?.edge_tier ?? 6)) * 0.05) * 100).toFixed(0)}%`,
      reason:
        (entry.l10_edge?.edge_tier ?? 6) <= 2
          ? 'Promoted tier — historical edge confirmed'
          : 'Mid tier — smaller size',
      edge: {
        tier: entry.l10_edge?.edge_tier ?? 6,
        hit: 0.42 + (7 - (entry.l10_edge?.edge_tier ?? 6)) * 0.05,
        ci_lo: 0.32 + (7 - (entry.l10_edge?.edge_tier ?? 6)) * 0.04,
        ci_hi: 0.55 + (7 - (entry.l10_edge?.edge_tier ?? 6)) * 0.05,
        n: 20 + (7 - (entry.l10_edge?.edge_tier ?? 6)) * 18,
        setup: setupTypeLabels[entry.l8_thesis.setup_type] ?? entry.l8_thesis.setup_type.toString(),
        regime: ctx.regime,
      },
    },
  };
}

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
  // entry may be a basic RankingEntry cast as SymbolFactorBreakdown by callers
  // that haven't fetched factor data yet (e.g. auto-select on first ranking
  // load). evaluateLayers crashes on the nested fields, so guard upstream.
  const hasFactorData =
    entry != null &&
    (entry as Partial<SymbolFactorBreakdown>).l2_universe != null &&
    (entry as Partial<SymbolFactorBreakdown>).l3_signals != null &&
    (entry as Partial<SymbolFactorBreakdown>).l5_scores != null &&
    (entry as Partial<SymbolFactorBreakdown>).l8_thesis != null;

  const layers = useMemo(() => {
    if (!entry || !hasFactorData) return null;
    return evaluateLayers(entry, ctx);
  }, [entry, ctx, hasFactorData]);

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
            {entry.l4_sector.sector_name} · Price {(entry.price ?? 0).toFixed(1)}
          </span>
        </div>
        <div className="text-[11px] text-[var(--text-secondary)]">
          {isLong ? 'Bullish' : 'Bearish'} thesis via {setupTypeLabels[entry.l8_thesis.setup_type] ?? entry.l8_thesis.setup_type} ·{' '}
          {entry.l7_confluence.score}/6 confluence · Composite{' '}
          <span className="font-mono font-bold">{entry.l5_scores.total.toFixed(1)}</span> · Net R:R{' '}
          <span className="font-mono font-bold">{entry.l8_thesis.net_rr.toFixed(2)}</span> ·{' '}
          <span
            className="font-semibold"
            style={{
              color:
                entry.l8_thesis.grade === 'ATTRACTIVE'
                  ? 'var(--trade-long)'
                  : entry.l8_thesis.grade === 'MARGINAL'
                    ? 'var(--trade-neutral)'
                    : 'var(--text-tertiary)',
            }}
          >
            {entry.l8_thesis.grade}
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
