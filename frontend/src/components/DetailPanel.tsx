'use client';

import { useMarketStore } from '@/stores/marketStore';
import { useFactorBreakdown } from '@/hooks/useFactorBreakdown';
import { setupTypeLabels } from '@/types/api';
import type { ThesisCard } from '@/types/api';

interface DetailHeaderProps {
  thesis: ThesisCard;
  price: number;
  changePct: number;
  sector: string;
}

function DetailHeader({ thesis, price, changePct, sector }: DetailHeaderProps) {
  const isLong = thesis.direction === 'LONG';
  const dirColor = isLong ? 'var(--trade-long)' : 'var(--trade-short)';
  const gradeColor =
    thesis.grade === 'ATTRACTIVE'
      ? 'var(--trade-long)'
      : thesis.grade === 'MARGINAL'
        ? 'var(--trade-neutral)'
        : 'var(--trade-short)';

  return (
    <div
      className="flex items-center gap-2.5 border-b border-[var(--border-subtle)] px-3 py-2.5"
      style={{
        background: isLong ? 'var(--trade-long-dim)' : 'var(--trade-short-dim)',
      }}
    >
      <span className="h-1 w-4 rounded" style={{ background: dirColor }} />
      <div className="flex flex-col leading-tight">
        <div className="flex items-center gap-2">
          <span className="text-base font-bold">{thesis.symbol}</span>
          <span className="text-[11px] font-bold" style={{ color: dirColor }}>
            {thesis.direction}
          </span>
          <span className="text-[10px] text-[var(--text-tertiary)]">· {sector}</span>
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className="font-mono text-sm font-semibold tabular-nums">₹{price.toFixed(2)}</span>
          <span
            className="font-mono text-[11px]"
            style={{ color: changePct >= 0 ? 'var(--trade-long)' : 'var(--trade-short)' }}
          >
            {changePct >= 0 ? '+' : ''}{changePct.toFixed(2)}%
          </span>
          <span className="text-[10px] text-[var(--text-tertiary)]">· {setupTypeLabels[thesis.setup_type]}</span>
        </div>
      </div>
      <div className="flex-1" />
      <div className="flex flex-col items-end">
        <span className="text-[9px] uppercase tracking-wide text-[var(--text-tertiary)]">Grade</span>
        <span className="text-lg font-extrabold tracking-wide" style={{ color: gradeColor }}>
          {thesis.grade}
        </span>
      </div>
      <span className="rounded bg-[var(--bg-surface-raised)] px-1.5 py-0.5 font-mono text-[10px]">
        L{thesis.actionability_tier === 'Tradeable' ? '10·T1' : thesis.actionability_tier === 'Constrained' ? '10·T3' : '10·T6'}
      </span>
      <div className="flex flex-col items-end">
        <span className="text-[9px] uppercase tracking-wide text-[var(--text-tertiary)]">Valid Until</span>
        <span className="font-mono text-[10px] text-[var(--text-secondary)]">
          {new Date(thesis.valid_until).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </div>
  );
}

function LevelsChart({ thesis, price, vwap }: { thesis: ThesisCard; price: number; vwap: number }) {
  const isLong = thesis.direction === 'LONG';
  const high = isLong ? thesis.t2 : thesis.invalidation;
  const low = isLong ? thesis.invalidation : thesis.t2;
  const range = high - low;
  const pos = (v: number) => ((v - low) / range) * 100;

  const rewardR = Math.abs(thesis.t1 - thesis.trigger) / Math.abs(thesis.trigger - thesis.invalidation);
  const t2R = Math.abs(thesis.t2 - thesis.trigger) / Math.abs(thesis.trigger - thesis.invalidation);

  const deltaLabel = (v: number) => {
    const d = ((v - price) / price) * 100;
    return `${d >= 0 ? '+' : ''}${d.toFixed(2)}%`;
  };

  return (
    <div className="rounded border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] p-2">
      <div className="mb-2 flex items-center gap-2">
        <span className="text-[10px] uppercase tracking-wide text-[var(--text-tertiary)]">L8 · Price Levels</span>
        <span className="flex-1" />
        <span className="rounded bg-[var(--bg-surface)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--text-secondary)]">
          ×{thesis.time_decay_multiplier.toFixed(2)} decay
        </span>
        <span className="font-mono text-[10px] text-[var(--text-tertiary)]">
          gross R:R <span className="text-[var(--text-primary)]">{thesis.gross_rr.toFixed(2)}</span>
        </span>
        <span className="font-mono text-[10px] text-[var(--text-tertiary)]">
          net{' '}
          <span
            style={{
              color: thesis.net_rr >= 1.1 ? 'var(--trade-long)' : 'var(--text-primary)',
            }}
          >
            {thesis.net_rr.toFixed(2)}
          </span>
        </span>
      </div>

      {/* Simple price ladder */}
      <div
        className="relative mb-2 overflow-hidden rounded"
        style={{
          background: `linear-gradient(180deg, var(--trade-long-dim) 0%, transparent 50%, var(--trade-short-dim) 100%)`,
          minHeight: 120,
        }}
      >
        {[
          { label: 'T2', v: thesis.t2, color: 'var(--trade-long)', style: 'solid' },
          { label: 'T1', v: thesis.t1, color: 'var(--trade-long)', style: 'dashed' },
          { label: 'VWAP', v: vwap, color: 'var(--trade-neutral)', style: 'dotted' },
          { label: 'Trigger', v: thesis.trigger, color: 'var(--accent)', style: 'solid' },
          { label: 'Now', v: price, color: 'var(--text-primary)', style: 'solid' },
          { label: 'Invalidation', v: thesis.invalidation, color: 'var(--trade-short)', style: 'solid' },
        ]
          .sort((a, b) => b.v - a.v)
          .map((item) => (
            <div
              key={item.label}
              className="absolute left-2 right-2 h-px"
              style={{
                top: `${100 - pos(item.v)}%`,
                borderTop: `1px ${item.style} ${item.color}`,
                opacity: item.label === 'Now' || item.label === 'Trigger' || item.label === 'Invalidation' ? 1 : 0.6,
              }}
            >
              <span
                className="absolute -top-3 left-0 bg-[var(--bg-surface-raised)] px-1 text-[9px] font-bold"
                style={{ color: item.color }}
              >
                {item.label.toUpperCase()}
              </span>
              <span className="absolute -top-3 right-0 bg-[var(--bg-surface-raised)] px-1 font-mono text-[10px]" style={{ color: item.color }}>
                {item.v.toFixed(2)}
              </span>
              {(item.label === 'T2' || item.label === 'T1' || item.label === 'VWAP' || item.label === 'Invalidation') && (
                <span
                  className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[var(--bg-surface-raised)] px-1 font-mono text-[9px] tabular-nums"
                  style={{ color: 'var(--text-tertiary)' }}
                >
                  {deltaLabel(item.v)}
                </span>
              )}
            </div>
          ))}
      </div>

      {/* R:R bar */}
      <div className="flex items-center gap-1.5 text-[10px]">
        <span style={{ color: 'var(--trade-short)' }}>−1R</span>
        <div className="relative h-1.5 flex-1 rounded-full bg-[var(--bg-base)]">
          <div className="absolute left-1/2 top-0 h-full w-0.5 -translate-x-1/2 bg-[var(--accent)]" />
          <div
            className="absolute top-0 h-full w-0.5 bg-[var(--trade-long)]"
            style={{ left: `${50 + (rewardR / (t2R + 1)) * 50 * 0.6}%` }}
          />
          <div
            className="absolute top-0 h-full w-0.5 bg-[var(--trade-long)]"
            style={{ left: `${50 + (t2R / (t2R + 1)) * 50}%` }}
          />
        </div>
        <span style={{ color: 'var(--trade-long)' }}>+{t2R.toFixed(1)}R</span>
      </div>
    </div>
  );
}

interface FactorBarProps {
  label: string;
  value: number;
  weight: number;
}

function FactorBar({ label, value, weight }: FactorBarProps) {
  const color =
    value >= 75 ? 'var(--trade-long)' : value >= 55 ? 'var(--trade-neutral)' : 'var(--trade-short)';
  return (
    <div className="flex items-center gap-2 text-[11px]">
      <span className="w-20 text-[var(--text-secondary)]">{label}</span>
      <span className="w-6 font-mono text-[10px] text-[var(--text-tertiary)]">×{weight.toFixed(2)}</span>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[var(--bg-surface-raised)]">
        <div className="h-full rounded-full" style={{ width: `${value}%`, background: color }} />
      </div>
      <span className="w-6 text-right font-mono font-semibold tabular-nums">{value}</span>
    </div>
  );
}

interface LayerCardProps {
  tag: string;
  title: string;
  status: 'pass' | 'fail' | 'warn' | null;
  children: React.ReactNode;
}

function LayerCard({ tag, title, status, children }: LayerCardProps) {
  const statusColor =
    status === 'pass'
      ? 'var(--trade-long)'
      : status === 'fail'
        ? 'var(--trade-short)'
        : status === 'warn'
          ? 'var(--trade-neutral)'
          : 'var(--text-tertiary)';

  return (
    <div className="overflow-hidden rounded border border-[var(--border-subtle)] bg-[var(--var(--bg-surface))]">
      <div
        className="flex items-center gap-1.5 border-b border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] px-2.5 py-1.5"
      >
        <span
          className="rounded px-1.5 py-0.5 text-[9px] font-bold"
          style={{
            background: 'var(--bg-base)',
            color: statusColor,
          }}
        >
          {tag}
        </span>
        <span className="text-[11px] font-semibold text-[var(--text-secondary)]">{title}</span>
        <span className="flex-1" />
        <span className="h-1.5 w-1.5 rounded-full" style={{ background: statusColor }} />
      </div>
      <div className="p-2.5">{children}</div>
    </div>
  );
}

interface KVProps {
  label: string;
  value: string | number;
  color?: string;
  mono?: boolean;
}

function KV({ label, value, color, mono = true }: KVProps) {
  return (
    <div className="flex justify-between text-[11px]">
      <span className="text-[var(--text-tertiary)]">{label}</span>
      <span
        className={mono ? 'font-mono tabular-nums font-semibold' : 'font-semibold'}
        style={{ color: color || 'var(--text-primary)' }}
      >
        {value}
      </span>
    </div>
  );
}

function ConfluenceList({ checks }: { checks: Record<string, boolean> }) {
  const labels: Record<string, string> = {
    strong_close: 'Strong Close',
    volume_confirm: 'Volume Confirm',
    non_exhaustion: 'Non-Exhaustion',
    htf_alignment: 'HTF Alignment',
    risk_distance: 'Risk Distance',
    reward_distance: 'Reward Distance',
  };
  return (
    <div className="space-y-1.5">
      {Object.entries(labels).map(([key, label]) => {
        const ok = checks[key];
        return (
          <div key={key} className="flex items-center gap-1.5 text-[11px]">
            <span
              className="flex h-3 w-3 items-center justify-center rounded text-[8px] font-extrabold"
              style={{
                background: ok ? 'var(--trade-long-dim)' : 'var(--trade-short-dim)',
                color: ok ? 'var(--trade-long)' : 'var(--trade-short)',
              }}
            >
              {ok ? '✓' : '✕'}
            </span>
            <span className="text-[var(--text-primary)]">{label}</span>
          </div>
        );
      })}
    </div>
  );
}

interface DetailPanelProps {
  symbol: string;
}

export function DetailPanel({ symbol }: DetailPanelProps) {
  const { data, isLoading } = useFactorBreakdown(symbol);

  if (isLoading) {
    return (
      <div className="flex flex-col rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
        <div className="h-12 animate-pulse border-b border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]" />
        <div className="flex-1 p-4">
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 animate-pulse rounded bg-[var(--bg-surface-raised)]" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex min-h-[200px] items-center justify-center rounded-lg border border-dashed border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 text-center">
        <div>
          <div className="text-sm text-[var(--text-secondary)]">Select a symbol</div>
          <div className="mt-1 text-xs text-[var(--text-tertiary)]">
            Tap any row in Top 25 LONG or SHORT to see how layers L2–L10 contribute
          </div>
        </div>
      </div>
    );
  }

  const thesis = useMarketStore.getState().theses.find((t) => t.symbol === symbol);
  const price = data.l3_signals.vwap * 1.002; // Approximate price
  const changePct = 0.85;

  // Determine layer statuses
  const l2_status = data.l2_universe.fo_ban ? 'fail' : data.l2_universe.lqs_score < 0.7 ? 'warn' : 'pass';
  const l3_status = data.l3_signals.ema_aligned ? 'pass' : 'warn';
  const l4_status =
    data.l4_sector.rs_ratio > 1.02 && data.l4_sector.rs_momentum > 1
      ? 'pass'
      : data.l4_sector.rs_ratio < 0.98
        ? 'fail'
        : 'warn';
  const l5_status = data.l5_scores.total >= 75 ? 'pass' : data.l5_scores.total >= 60 ? 'warn' : 'fail';

  const weights = { trend: 0.20, momentum: 0.18, volume: 0.15, volpos: 0.12, structure: 0.13, sector: 0.12, risk: 0.10 };

  return (
    <div className="flex flex-col overflow-hidden rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
      {/* Header */}
      {thesis && <DetailHeader thesis={thesis} price={price} changePct={changePct} sector={data.l4_sector.sector_name} />}

      <div className="flex-1 overflow-y-auto p-3">
        <div className="space-y-3">
          {/* Levels chart */}
          {thesis && <LevelsChart thesis={thesis} price={price} vwap={data.l3_signals.vwap} />}

          {/* L2 / L3 / L4 cards */}
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            <LayerCard tag="L2" title="Universe" status={l2_status}>
              <div className="space-y-1">
                <KV
                  label="F&O"
                  value={data.l2_universe.fo_eligible ? 'Eligible' : 'Ineligible'}
                  color={data.l2_universe.fo_eligible ? 'var(--trade-long)' : 'var(--trade-short)'}
                  mono={false}
                />
                <KV
                  label="Ban-list"
                  value={data.l2_universe.fo_ban ? 'YES' : 'No'}
                  color={data.l2_universe.fo_ban ? 'var(--trade-short)' : 'var(--text-primary)'}
                  mono={false}
                />
                <KV label="MWPL" value={data.l2_universe.mwpl_status} mono={false} />
                <KV
                  label="Earnings"
                  value={data.l2_universe.earnings_flag}
                  color={data.l2_universe.earnings_flag !== 'None' ? 'var(--trade-neutral)' : 'var(--text-primary)'}
                  mono={false}
                />
                <KV
                  label="LQS"
                  value={`${data.l2_universe.liquidity_quality} · ${(data.l2_universe.lqs_score * 100).toFixed(0)}`}
                />
              </div>
            </LayerCard>

            <LayerCard tag="L3" title="Signals" status={l3_status}>
              <div className="space-y-1">
                <KV
                  label="EMA Stack"
                  value={data.l3_signals.ema_aligned ? 'Aligned' : 'Mixed'}
                  color={data.l3_signals.ema_aligned ? 'var(--trade-long)' : 'var(--trade-short)'}
                  mono={false}
                />
                <KV label="RSI / ADX" value={`${data.l3_signals.rsi.toFixed(1)} / ${data.l3_signals.adx.toFixed(1)}`} />
                <KV
                  label="MACD hist"
                  value={data.l3_signals.macd_hist.toFixed(2)}
                  color={data.l3_signals.macd_hist >= 0 ? 'var(--trade-long)' : 'var(--trade-short)'}
                />
                <KV label="ATR%" value={`${data.l3_signals.atr_pct.toFixed(2)}%`} />
                <KV
                  label="vs VWAP"
                  value={`${data.l3_signals.above_vwap ? '+' : '−'}${Math.abs(((price - data.l3_signals.vwap) / data.l3_signals.vwap) * 100).toFixed(2)}%`}
                  color={data.l3_signals.above_vwap ? 'var(--trade-long)' : 'var(--trade-short)'}
                />
              </div>
            </LayerCard>

            <LayerCard tag="L4" title="Sector" status={l4_status}>
              <div className="space-y-1">
                <KV label="Sector" value={`${data.l4_sector.sector_name} · #${data.l4_sector.rotation_rank}`} mono={false} />
                <KV
                  label="RS-Ratio"
                  value={data.l4_sector.rs_ratio.toFixed(3)}
                  color={data.l4_sector.rs_ratio > 1.02 ? 'var(--trade-long)' : data.l4_sector.rs_ratio < 0.98 ? 'var(--trade-short)' : 'var(--text-primary)'}
                />
                <KV
                  label="RS-Momentum"
                  value={data.l4_sector.rs_momentum.toFixed(3)}
                  color={data.l4_sector.rs_momentum > 1 ? 'var(--trade-long)' : 'var(--trade-short)'}
                />
              </div>
            </LayerCard>
          </div>

          {/* L5 Score breakdown */}
          <LayerCard tag="L5" title={`Scoring · Total ${data.l5_scores.total.toFixed(1)}`} status={l5_status}>
            <div className="space-y-1.5">
              <FactorBar label="F1 Trend" value={data.l5_scores.f1_trend} weight={weights.trend} />
              <FactorBar label="F2 Momentum" value={data.l5_scores.f2_momentum} weight={weights.momentum} />
              <FactorBar label="F3 Volume" value={data.l5_scores.f3_volume} weight={weights.volume} />
              <FactorBar label="F4 Vol-Pos" value={data.l5_scores.f4_volpos} weight={weights.volpos} />
              <FactorBar label="F5 Structure" value={data.l5_scores.f5_structure} weight={weights.structure} />
              <FactorBar label="F6 Sector" value={data.l5_scores.f6_sector} weight={weights.sector} />
              <FactorBar label="F7 Risk" value={data.l5_scores.f7_risk} weight={weights.risk} />
            </div>
            <div className="mt-2 border-t border-[var(--border-subtle)] pt-2 text-[10px] text-[var(--text-tertiary)]">
              regime: <span className="text-[var(--text-primary)]">{data.l5_scores.regime}</span> · weights conditioned on regime
            </div>
          </LayerCard>

          {/* L7 Confluence */}
          <LayerCard
            tag="L7"
            title={`Confluence · ${data.l7_confluence.score}/${data.l7_confluence.max}`}
            status={data.l7_confluence.score >= 5 ? 'pass' : data.l7_confluence.score >= 3 ? 'warn' : 'fail'}
          >
            <ConfluenceList checks={data.l7_confluence.checks} />
          </LayerCard>

          {/* L6 Ranking */}
          <LayerCard tag="L6" title="Ranking" status={null}>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              <KV label="Score now" value={data.l6_ranking.previous_score.toFixed(1)} />
              <KV
                label="Prev cycle"
                value={(data.l6_ranking.previous_score - data.l6_ranking.score_change).toFixed(1)}
              />
              <KV
                label="Δ"
                value={`${data.l6_ranking.score_change >= 0 ? '+' : ''}${data.l6_ranking.score_change.toFixed(1)}`}
                color={data.l6_ranking.score_change > 0 ? 'var(--trade-long)' : data.l6_ranking.score_change < 0 ? 'var(--trade-short)' : 'var(--text-primary)'}
              />
              <KV
                label="Movement"
                value={data.l6_ranking.rank_movement}
                color={data.l6_ranking.rank_movement === 'NEW' ? 'var(--trade-long)' : data.l6_ranking.rank_movement === 'UP' ? 'var(--trade-long)' : data.l6_ranking.rank_movement === 'DOWN' ? 'var(--trade-short)' : 'var(--text-primary)'}
                mono={false}
              />
              <KV label="Liquidity" value={data.l6_ranking.liquidity_quality} mono={false} />
            </div>
          </LayerCard>

          {/* L8 Thesis summary */}
          {data.l8_thesis && thesis && (
            <LayerCard tag="L8" title="Thesis" status={null}>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                <KV label="Trigger" value={`₹${data.l8_thesis.trigger.toFixed(2)}`} />
                <KV label="Invalidation" value={`₹${data.l8_thesis.invalidation.toFixed(2)}`} color="var(--trade-short)" />
                <KV label="T1" value={`₹${data.l8_thesis.t1.toFixed(2)}`} color="var(--trade-long)" />
                <KV label="T2" value={`₹${data.l8_thesis.t2.toFixed(2)}`} color="var(--trade-long)" />
                <KV label="Gross R:R" value={data.l8_thesis.gross_rr.toFixed(2)} />
                <KV label="Net R:R" value={data.l8_thesis.net_rr.toFixed(2)} color={data.l8_thesis.net_rr >= 1.1 ? 'var(--trade-long)' : 'var(--text-primary)'} />
                <KV label="Decay" value={`×${thesis.time_decay_multiplier.toFixed(2)}`} />
                <KV
                  label="Valid Until"
                  value={new Date(thesis.valid_until).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                  mono={false}
                />
                <KV label="Tier" value={data.l8_thesis.actionability_tier} mono={false} />
                <KV label="Grade" value={data.l8_thesis.grade} color={data.l8_thesis.grade === 'ATTRACTIVE' ? 'var(--trade-long)' : 'var(--text-primary)'} mono={false} />
                <KV label="thesis_id" value={data.l8_thesis.thesis_id.slice(0, 8)} mono={true} />
              </div>
            </LayerCard>
          )}

          {/* L9 + L10 row */}
          {thesis && (
            <div className="grid grid-cols-2 gap-2">
              <LayerCard tag="L9" title="Monitor" status={null}>
                <div className="space-y-1">
                  <KV label="State" value="PENDING" mono={false} />
                  <KV label="MFE" value="—" />
                  <KV label="MAE" value="—" />
                  <KV label="Mode" value="Shadow" mono={false} />
                </div>
              </LayerCard>
              <LayerCard tag="L10" title="Edge" status={null}>
                <div className="space-y-1">
                  <KV label="Setup" value={setupTypeLabels[thesis.setup_type]} mono={false} />
                  <KV
                    label="Regime match"
                    value={thesis.preferred_regime === 'Trending-Up' ? '↑Trending' : thesis.preferred_regime === 'Trending-Down' ? '↓Trending' : 'Range'}
                    color={thesis.preferred_regime === 'Trending-Up' ? 'var(--trade-long)' : thesis.preferred_regime === 'Trending-Down' ? 'var(--trade-short)' : 'var(--trade-neutral)'}
                    mono={false}
                  />
                  <KV label="Hit rate" value="—" />
                  <KV label="Wilson 95% CI" value="—" />
                  <KV label="N samples" value="—" />
                </div>
              </LayerCard>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}