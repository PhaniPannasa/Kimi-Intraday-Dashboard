'use client';

import { useMemo, useState } from 'react';
import { cn } from '@/lib/utils';
import { LAYER_META, SECTORS, setupTypeLabels } from '@/types/api';
import type { SymbolFactorBreakdown, MarketContextFrame } from '@/types/api';
import { StatTile, MiniBar, Histogram, StockTable, VerdictPill, SectionHeader } from './SharedComponents';
import type { StockColumn } from './SharedComponents';

/* ─── Helpers ────────────────────────────────────────── */
function binValues(
  values: number[],
  binSize: number,
  rangeStart: number,
  rangeEnd: number,
  fmt?: (s: number) => string,
): { label: string; value: number }[] {
  const bins: Record<string, number> = {};
  for (let s = rangeStart; s < rangeEnd; s += binSize) {
    bins[fmt ? fmt(s) : `${s}-${s + binSize}`] = 0;
  }
  for (const v of values) {
    if (v < rangeStart || v >= rangeEnd) continue;
    const idx = Math.min(
      Math.floor((v - rangeStart) / binSize),
      Math.floor((rangeEnd - rangeStart) / binSize) - 1,
    );
    const start = rangeStart + idx * binSize;
    const key = fmt ? fmt(start) : `${start}-${start + binSize}`;
    bins[key] = (bins[key] ?? 0) + 1;
  }
  return Object.entries(bins).map(([label, value]) => ({ label, value }));
}

function avg(arr: number[]): number {
  return arr.length > 0 ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;
}

function hasFactorData(stocks: any[]): boolean {
  return stocks.length > 0 && stocks.some(
    (s) => s != null && s.l2_universe != null && s.l3_signals != null && s.l5_scores != null
  );
}

function useAllStocks(stocks: any[]): any[] {
  // Filter to only stocks that have factor data (guard against RankingEntry[] input)
  const valid = stocks.filter(
    (s) => s != null && s.l2_universe != null && s.l3_signals != null && s.l5_scores != null
  );
  // If no valid stocks, return the full array anyway — sub-views may still render
  // partial data from any accessible fields, but the guard in LayerInspector
  // (see below) handles the case where stocks have no factor data at all
  return valid.length > 0 ? valid : stocks;
}

const LAYER_ORDER = ['L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8', 'L9', 'L10'];
const LAYER_INDEX: Record<string, number> = Object.fromEntries(
  LAYER_ORDER.map((k, i) => [k, i]),
);

/* ═══════════════════════════════════════════════════════
   L1 — Market Context
   ═══════════════════════════════════════════════════════ */
function L1View({ ctx, stocks }: { ctx: MarketContextFrame; stocks: SymbolFactorBreakdown[] }) {
  const all = useAllStocks(stocks);
  const sectorDist = useMemo(
    () =>
      SECTORS.map((s) => ({
        label: s.name.slice(0, 5),
        value: all.filter((st) => st.l4_sector.sector_id === s.id).length,
      })),
    [all],
  );
  const regimeColor =
    ctx.regime === 'Trending-Up'
      ? 'var(--trade-long)'
      : ctx.regime === 'Trending-Down'
        ? 'var(--trade-short)'
        : 'var(--trade-neutral)';

  return (
    <div className="space-y-3">
      {/* Regime hero */}
      <div
        className="rounded-md border p-4 text-center"
        style={{
          borderColor: `${regimeColor}44`,
          background: `linear-gradient(135deg, ${regimeColor}11, transparent)`,
        }}
      >
        <div className="text-[10px] font-medium uppercase tracking-wide text-[var(--text-tertiary)]">
          Current Regime
        </div>
        <div className="mt-1 text-2xl font-extrabold tracking-tight" style={{ color: regimeColor }}>
          {ctx.regime}
        </div>
        <div className="mt-1 flex items-center justify-center gap-3">
          <span className="font-mono text-sm tabular-nums" style={{ color: regimeColor }}>
            {(ctx.regime_confidence * 100).toFixed(0)}% confidence
          </span>
          <span className="text-[var(--border-subtle)]">|</span>
          <span
            className={cn(
              'rounded px-1.5 py-0.5 text-[10px] font-semibold',
              ctx.vix_band === 'Elevated'
                ? 'bg-[var(--trade-neutral-dim)] text-[var(--trade-neutral)]'
                : 'bg-[var(--bg-surface-elev)] text-[var(--text-secondary)]',
            )}
          >
            VIX {ctx.vix_band}
          </span>
        </div>
      </div>

      {/* Stats row */}
      <div className="flex flex-wrap gap-2">
        <StatTile
          label="India VIX"
          value={ctx.vix_value.toFixed(2)}
          hint={ctx.vix_trajectory}
          borderColor="var(--trade-neutral)"
        />
        <StatTile
          label="Breadth"
          value={ctx.breadth}
          borderColor={ctx.breadth === 'Strong' ? 'var(--trade-long)' : ctx.breadth === 'Weak' ? 'var(--trade-short)' : 'var(--trade-neutral)'}
          valueColor={ctx.breadth === 'Strong' ? 'var(--trade-long)' : ctx.breadth === 'Weak' ? 'var(--trade-short)' : 'var(--trade-neutral)'}
        />
        <StatTile
          label="Pre-Market"
          value={ctx.premarket_bias}
          borderColor={ctx.premarket_bias === 'Positive' ? 'var(--trade-long)' : ctx.premarket_bias === 'Negative' ? 'var(--trade-short)' : 'var(--text-tertiary)'}
        />
        <StatTile
          label="BankNifty Δ"
          value={`${ctx.bank_nifty_divergence >= 0 ? '+' : ''}${ctx.bank_nifty_divergence.toFixed(2)}%`}
          valueColor={
            Math.abs(ctx.bank_nifty_divergence) > 0.2
              ? ctx.bank_nifty_divergence > 0
                ? 'var(--trade-long)'
                : 'var(--trade-short)'
              : 'var(--text-secondary)'
          }
        />
        <StatTile label="Session" value={ctx.time_bucket} />
        {ctx.event_flag && (
          <StatTile
            label="Event"
            value={ctx.event_flag}
            borderColor="var(--trade-neutral)"
            valueColor="var(--trade-neutral)"
          />
        )}
      </div>

      {/* Sector distribution heatmap */}
      <div>
        <SectionHeader>Sector Distribution — {all.length} Stocks</SectionHeader>
        <Histogram data={sectorDist} barColor="var(--accent)" />
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   L2 — Universe
   ═══════════════════════════════════════════════════════ */
function L2View({ stocks, ctx: _ctx }: { stocks: SymbolFactorBreakdown[]; ctx: MarketContextFrame }) {
  const all = useAllStocks(stocks);
  const [sortKey, setSortKey] = useState<string | undefined>();
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [selectedSym, setSelectedSym] = useState<string | null>(null);

  const banned = all.filter((s) => s.l2_universe.fo_ban).length;
  const earnings = all.filter((s) => s.l2_universe.earnings_flag !== 'None').length;
  const mwpl = all.filter((s) => s.l2_universe.mwpl_status !== 'None').length;
  const avgLqs = avg(all.map((s) => s.l2_universe.lqs_score));
  const lqsHist = useMemo(
    () =>
      binValues(
        all.map((s) => s.l2_universe.lqs_score * 100),
        10,
        50,
        100,
        (v) => `${v}%`,
      ),
    [all],
  );

  const columns: StockColumn[] = useMemo(
    () => [
      { key: 'symbol', label: 'Symbol', render: (s) => <span className="font-semibold">{s.symbol}</span>, sortable: true, sortValue: (s) => s.symbol },
      { key: 'sector', label: 'Sector', render: (s) => <span className="text-[var(--text-secondary)]">{s.l4_sector.sector_name}</span>, sortable: true, sortValue: (s) => s.l4_sector.sector_name },
      { key: 'dir', label: 'Dir', render: (s) => <span style={{ color: s.direction === 'LONG' ? 'var(--trade-long)' : 'var(--trade-short)' }}>{s.direction === 'LONG' ? 'L' : 'S'}</span> },
      { key: 'fo', label: 'F&O', render: (s) => <span style={{ color: s.l2_universe.fo_eligible ? 'var(--trade-long)' : 'var(--trade-short)' }}>{s.l2_universe.fo_eligible ? '✓' : '✗'}</span> },
      { key: 'ban', label: 'Ban', render: (s) => <span style={{ color: s.l2_universe.fo_ban ? 'var(--trade-short)' : 'var(--trade-long)' }}>{s.l2_universe.fo_ban ? 'BAN' : '—'}</span> },
      { key: 'earn', label: 'Earn', render: (s) => <span style={{ color: s.l2_universe.earnings_flag !== 'None' ? 'var(--trade-neutral)' : 'var(--text-faint)' }}>{s.l2_universe.earnings_flag !== 'None' ? s.l2_universe.earnings_flag : '—'}</span> },
      { key: 'mwpl', label: 'MWPL', render: (s) => <span className="text-[var(--text-secondary)]">{s.l2_universe.mwpl_status !== 'None' ? s.l2_universe.mwpl_status : '—'}</span> },
      {
        key: 'lqs',
        label: 'LQS',
        sortable: true,
        sortValue: (s) => s.l2_universe.lqs_score,
        align: 'right',
        render: (s) => (
          <span
            style={{
              color:
                s.l2_universe.lqs_score > 0.85
                  ? 'var(--trade-long)'
                  : s.l2_universe.lqs_score > 0.7
                    ? 'var(--trade-neutral)'
                    : 'var(--trade-short)',
            }}
          >
            {(s.l2_universe.lqs_score * 100).toFixed(0)}
          </span>
        ),
      },
      {
        key: 'lq',
        label: 'Quality',
        render: (s) => (
          <span
            className="text-[9px]"
            style={{
              color:
                s.l2_universe.liquidity_quality === 'Excellent'
                  ? 'var(--trade-long)'
                  : s.l2_universe.liquidity_quality === 'Good'
                    ? 'var(--trade-neutral)'
                    : 'var(--text-tertiary)',
            }}
          >
            {s.l2_universe.liquidity_quality}
          </span>
        ),
      },
    ],
    [],
  );

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <StatTile label="Source" value={all.length} hint="Nifty 100" borderColor="var(--accent)" />
        <StatTile
          label="Survivors"
          value={all.length - banned}
          hint={`-${banned} banned`}
          borderColor="var(--trade-long)"
          valueColor="var(--trade-long)"
        />
        <StatTile
          label="Banned"
          value={banned}
          hint="F&O ban list"
          borderColor={banned > 0 ? 'var(--trade-short)' : 'var(--text-faint)'}
          valueColor={banned > 0 ? 'var(--trade-short)' : 'var(--text-secondary)'}
        />
        <StatTile
          label="Earnings"
          value={earnings}
          hint="T-1/Today"
          borderColor={earnings > 0 ? 'var(--trade-neutral)' : 'var(--text-faint)'}
        />
        <StatTile
          label="MWPL Hit"
          value={mwpl}
          borderColor={mwpl > 0 ? 'var(--trade-neutral)' : 'var(--text-faint)'}
        />
        <StatTile
          label="Avg LQS"
          value={(avgLqs * 100).toFixed(0)}
          hint="%"
          valueColor={avgLqs > 0.8 ? 'var(--trade-long)' : avgLqs > 0.65 ? 'var(--trade-neutral)' : 'var(--trade-short)'}
        />
      </div>

      {/* LQS Histogram */}
      <div>
        <SectionHeader>LQS Distribution</SectionHeader>
        <Histogram data={lqsHist} barColor="var(--accent)" />
      </div>

      {/* Stock table */}
      <SectionHeader>Universe Details</SectionHeader>
      <div className="max-h-72 overflow-y-auto rounded-md border border-[var(--border-subtle)]">
        <StockTable
          stocks={all}
          columns={columns}
          selectedSymbol={selectedSym}
          onSelect={(s) => setSelectedSym(s.symbol)}
          sortKey={sortKey}
          sortDir={sortDir}
          onSort={handleSort}
        />
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   L3 — Signals
   ═══════════════════════════════════════════════════════ */
function L3View({ stocks, ctx: _ctx }: { stocks: SymbolFactorBreakdown[]; ctx: MarketContextFrame }) {
  const all = useAllStocks(stocks);
  const [sortKey, setSortKey] = useState<string | undefined>();
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [selectedSym, setSelectedSym] = useState<string | null>(null);

  const emaAligned = all.filter((s) => s.l3_signals.ema_aligned).length;
  const aboveVwap = all.filter((s) => s.l3_signals.above_vwap).length;
  const adxStrong = all.filter((s) => s.l3_signals.adx > 25).length;
  const rsiExtreme = all.filter((s) => s.l3_signals.rsi > 70 || s.l3_signals.rsi < 30).length;

  const rsiHist = useMemo(
    () => binValues(all.map((s) => s.l3_signals.rsi), 10, 10, 100, (v) => `${v}`),
    [all],
  );

  const columns: StockColumn[] = useMemo(
    () => [
      { key: 'symbol', label: 'Symbol', render: (s) => <span className="font-semibold">{s.symbol}</span>, sortable: true, sortValue: (s) => s.symbol },
      { key: 'dir', label: 'Dir', render: (s) => <span style={{ color: s.direction === 'LONG' ? 'var(--trade-long)' : 'var(--trade-short)' }}>{s.direction === 'LONG' ? 'L' : 'S'}</span> },
      { key: 'ema', label: 'EMA', render: (s) => <span style={{ color: s.l3_signals.ema_aligned ? 'var(--trade-long)' : 'var(--trade-short)' }}>{s.l3_signals.ema_aligned ? '✓' : '✗'}</span> },
      { key: 'st', label: 'ST', render: (s) => <span style={{ color: s.l3_signals.supertrend_dir > 0 ? 'var(--trade-long)' : 'var(--trade-short)' }}>{s.l3_signals.supertrend_dir > 0 ? '↑' : '↓'}</span> },
      { key: 'adx', label: 'ADX', sortable: true, sortValue: (s) => s.l3_signals.adx, align: 'right', render: (s) => <span style={{ color: s.l3_signals.adx > 25 ? 'var(--trade-long)' : 'var(--text-tertiary)' }}>{s.l3_signals.adx.toFixed(0)}</span> },
      { key: 'rsi', label: 'RSI', sortable: true, sortValue: (s) => s.l3_signals.rsi, align: 'right', render: (s) => <span style={{ color: s.l3_signals.rsi > 70 ? 'var(--trade-short)' : s.l3_signals.rsi < 30 ? 'var(--trade-long)' : 'var(--text-secondary)' }}>{s.l3_signals.rsi.toFixed(0)}</span> },
      { key: 'macd', label: 'MACD', sortable: true, sortValue: (s) => s.l3_signals.macd_hist, align: 'right', render: (s) => <span style={{ color: s.l3_signals.macd_hist > 0 ? 'var(--trade-long)' : 'var(--trade-short)' }}>{s.l3_signals.macd_hist > 0 ? '+' : ''}{s.l3_signals.macd_hist.toFixed(2)}</span> },
      { key: 'atr', label: 'ATR%', sortable: true, sortValue: (s) => s.l3_signals.atr_pct, align: 'right', render: (s) => <span>{s.l3_signals.atr_pct.toFixed(2)}</span> },
      { key: 'bb', label: 'BB%', sortable: true, sortValue: (s) => s.l3_signals.bb_width, align: 'right', render: (s) => <span>{s.l3_signals.bb_width.toFixed(1)}</span> },
      { key: 'vwap', label: 'VWAP', render: (s) => <span style={{ color: s.l3_signals.above_vwap ? 'var(--trade-long)' : 'var(--trade-short)' }}>{s.l3_signals.above_vwap ? '↑' : '↓'}</span> },
    ],
    [],
  );

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <StatTile label="EMA Aligned" value={emaAligned} hint={`of ${all.length}`} borderColor="var(--trade-long)" valueColor="var(--trade-long)" />
        <StatTile label="Above VWAP" value={aboveVwap} hint={`of ${all.length}`} borderColor="var(--accent)" valueColor="var(--accent)" />
        <StatTile label="ADX > 25" value={adxStrong} hint="Strong trend" borderColor="var(--trade-neutral)" />
        <StatTile label="RSI Extreme" value={rsiExtreme} hint=">70 or <30" borderColor={rsiExtreme > 0 ? 'var(--trade-short)' : 'var(--text-faint)'} valueColor={rsiExtreme > 0 ? 'var(--trade-short)' : 'var(--text-secondary)'} />
      </div>

      <div>
        <SectionHeader>RSI Distribution</SectionHeader>
        <Histogram data={rsiHist} barColor="var(--accent)" />
      </div>

      <SectionHeader>Signal Details ({all.length} stocks)</SectionHeader>
      <div className="max-h-72 overflow-y-auto rounded-md border border-[var(--border-subtle)]">
        <StockTable
          stocks={all}
          columns={columns}
          selectedSymbol={selectedSym}
          onSelect={(s) => setSelectedSym(s.symbol)}
          sortKey={sortKey}
          sortDir={sortDir}
          onSort={handleSort}
        />
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   L4 — Sector
   ═══════════════════════════════════════════════════════ */
function L4View({ stocks, ctx: _ctx }: { stocks: SymbolFactorBreakdown[]; ctx: MarketContextFrame }) {
  const all = useAllStocks(stocks);

  const sectorData = useMemo(
    () =>
      SECTORS.map((s) => {
        const sectorStocks = all.filter((st) => st.l4_sector.sector_id === s.id);
        const longs = sectorStocks.filter((st) => st.direction === 'LONG').length;
        const shorts = sectorStocks.filter((st) => st.direction === 'SHORT').length;
        const avgRs = avg(sectorStocks.map((st) => st.l4_sector.rs_ratio));
        const avgMom = avg(sectorStocks.map((st) => st.l4_sector.rs_momentum));
        const avgRoc = avg(sectorStocks.map((st) => st.l3_signals.roc_20));
        return {
          sector: s.name,
          id: s.id,
          count: sectorStocks.length,
          longs,
          shorts,
          avgRs,
          avgMom,
          avgRoc,
        };
      })
        .filter((s) => s.count > 0)
        .sort((a, b) => b.avgRs - a.avgRs),
    [all],
  );

  const leadingPicks = useMemo(
    () =>
      all
        .filter((s) => s.l4_sector.rs_ratio > 1.02 && s.l4_sector.rs_momentum > 1)
        .sort((a, b) => b.l4_sector.rs_ratio - a.l4_sector.rs_ratio)
        .slice(0, 8),
    [all],
  );

  return (
    <div className="space-y-3">
      {/* Sector strength table */}
      <SectionHeader>Sector Strength Rankings</SectionHeader>
      <div className="overflow-x-auto rounded-md border border-[var(--border-subtle)]">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="border-b border-[var(--border-subtle)] text-[10px] text-[var(--text-tertiary)]">
              <th className="px-2 py-1.5 text-left font-medium uppercase tracking-wide">Sector</th>
              <th className="px-2 py-1.5 text-right font-medium uppercase tracking-wide">#</th>
              <th className="px-2 py-1.5 text-right font-medium uppercase tracking-wide">L/S</th>
              <th className="px-2 py-1.5 text-right font-medium uppercase tracking-wide">RS-Ratio</th>
              <th className="px-2 py-1.5 text-right font-medium uppercase tracking-wide">RS-Mom</th>
              <th className="px-2 py-1.5 text-right font-medium uppercase tracking-wide">ROC20</th>
            </tr>
          </thead>
          <tbody>
            {sectorData.map((s) => (
              <tr key={s.id} className="border-b border-[var(--border-subtle)]/50 hover:bg-[var(--bg-surface-raised)]/30">
                <td className="px-2 py-1.5 font-medium">{s.sector}</td>
                <td className="px-2 py-1.5 text-right font-mono tabular-nums text-[var(--text-secondary)]">{s.count}</td>
                <td className="px-2 py-1.5 text-right font-mono tabular-nums">
                  <span className="text-[var(--trade-long)]">{s.longs}</span>
                  <span className="text-[var(--text-tertiary)]">/</span>
                  <span className="text-[var(--trade-short)]">{s.shorts}</span>
                </td>
                <td
                  className="px-2 py-1.5 text-right font-mono tabular-nums"
                  style={{ color: s.avgRs > 1.02 ? 'var(--trade-long)' : s.avgRs < 0.98 ? 'var(--trade-short)' : 'var(--text-secondary)' }}
                >
                  {s.avgRs.toFixed(3)}
                </td>
                <td
                  className="px-2 py-1.5 text-right font-mono tabular-nums"
                  style={{ color: s.avgMom > 1.02 ? 'var(--trade-long)' : s.avgMom < 0.98 ? 'var(--trade-short)' : 'var(--text-secondary)' }}
                >
                  {s.avgMom.toFixed(3)}
                </td>
                <td
                  className="px-2 py-1.5 text-right font-mono tabular-nums"
                  style={{ color: s.avgRoc > 0 ? 'var(--trade-long)' : s.avgRoc < 0 ? 'var(--trade-short)' : 'var(--text-secondary)' }}
                >
                  {s.avgRoc >= 0 ? '+' : ''}{s.avgRoc.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Leading sector picks */}
      {leadingPicks.length > 0 && (
        <div>
          <SectionHeader>{'Leading Sector Picks (RS-Ratio > 1.02 & RS-Mom > 1.0)'}</SectionHeader>
          <div className="flex flex-wrap gap-2">
            {leadingPicks.map((s) => (
              <div
                key={s.symbol}
                className="flex items-center gap-1.5 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/30 px-2 py-1"
              >
                <span className="text-[11px] font-semibold">{s.symbol}</span>
                <span className="text-[9px] text-[var(--text-tertiary)]">{s.l4_sector.sector_name}</span>
                <span
                  className="font-mono text-[10px] tabular-nums"
                  style={{ color: s.direction === 'LONG' ? 'var(--trade-long)' : 'var(--trade-short)' }}
                >
                  {s.direction === 'LONG' ? 'L' : 'S'}
                </span>
                <span className="font-mono text-[9px] text-[var(--text-secondary)]">
                  RS {s.l4_sector.rs_ratio.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   L5 — Scoring
   ═══════════════════════════════════════════════════════ */
function L5View({ stocks, ctx: _ctx }: { stocks: SymbolFactorBreakdown[]; ctx: MarketContextFrame }) {
  const all = useAllStocks(stocks);
  const [sortKey, setSortKey] = useState<string | undefined>();
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [selectedSym, setSelectedSym] = useState<string | null>(null);

  const scores = all.map((s) => s.l5_scores.total);
  const minScore = Math.min(...scores);
  const maxScore = Math.max(...scores);
  const avgScore = avg(scores);

  const scoreHist = useMemo(
    () => binValues(scores, 10, 10, 100, (v) => `${v}`),
    [scores],
  );

  const factorMeta = [
    { key: 'f1_trend', label: 'Trend' },
    { key: 'f2_momentum', label: 'Momentum' },
    { key: 'f3_volume', label: 'Volume' },
    { key: 'f4_volpos', label: 'Vol-Pos' },
    { key: 'f5_structure', label: 'Structure' },
    { key: 'f6_sector', label: 'Sector' },
    { key: 'f7_risk', label: 'Risk' },
  ];
  const weights = [0.2, 0.18, 0.15, 0.12, 0.13, 0.12, 0.1];
  const factorAvgs = factorMeta.map((f, i) => ({
    ...f,
    avg: avg(all.map((s) => (s.l5_scores as any)[f.key.replace('f', 'f')] as number)),
    weight: weights[i],
  }));

  const topScored = useMemo(
    () => [...all].sort((a, b) => b.l5_scores.total - a.l5_scores.total),
    [all],
  );

  const columns: StockColumn[] = useMemo(
    () => [
      { key: 'symbol', label: 'Symbol', render: (s) => <span className="font-semibold">{s.symbol}</span>, sortable: true, sortValue: (s) => s.symbol },
      { key: 'dir', label: 'Dir', render: (s) => <span style={{ color: s.direction === 'LONG' ? 'var(--trade-long)' : 'var(--trade-short)' }}>{s.direction === 'LONG' ? 'L' : 'S'}</span> },
      { key: 'sector', label: 'Sector', render: (s) => <span className="text-[var(--text-secondary)]">{s.l4_sector.sector_name}</span> },
      { key: 'score', label: 'Score', sortable: true, sortValue: (s) => s.l5_scores.total, align: 'right', render: (s) => <span className="font-bold" style={{ color: s.l5_scores.total >= 75 ? 'var(--trade-long)' : s.l5_scores.total >= 60 ? 'var(--trade-neutral)' : 'var(--trade-short)' }}>{s.l5_scores.total.toFixed(1)}</span> },
      { key: 'trend', label: 'T', sortable: true, sortValue: (s) => s.l5_scores.f1_trend, align: 'right', render: (s) => <span>{s.l5_scores.f1_trend}</span> },
      { key: 'mom', label: 'M', sortable: true, sortValue: (s) => s.l5_scores.f2_momentum, align: 'right', render: (s) => <span>{s.l5_scores.f2_momentum}</span> },
      { key: 'vol', label: 'V', sortable: true, sortValue: (s) => s.l5_scores.f3_volume, align: 'right', render: (s) => <span>{s.l5_scores.f3_volume}</span> },
      { key: 'vp', label: 'VP', sortable: true, sortValue: (s) => s.l5_scores.f4_volpos, align: 'right', render: (s) => <span>{s.l5_scores.f4_volpos}</span> },
      { key: 'str', label: 'St', sortable: true, sortValue: (s) => s.l5_scores.f5_structure, align: 'right', render: (s) => <span>{s.l5_scores.f5_structure}</span> },
      { key: 'sec', label: 'Sc', sortable: true, sortValue: (s) => s.l5_scores.f6_sector, align: 'right', render: (s) => <span>{s.l5_scores.f6_sector}</span> },
      { key: 'risk', label: 'R', sortable: true, sortValue: (s) => s.l5_scores.f7_risk, align: 'right', render: (s) => <span>{s.l5_scores.f7_risk}</span> },
    ],
    [],
  );

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <StatTile label="Avg Score" value={avgScore.toFixed(1)} hint="Composite" borderColor="var(--accent)" valueColor="var(--accent)" />
        <StatTile label="Min" value={minScore.toFixed(1)} borderColor="var(--trade-short)" valueColor="var(--trade-short)" />
        <StatTile label="Max" value={maxScore.toFixed(1)} borderColor="var(--trade-long)" valueColor="var(--trade-long)" />
      </div>

      <div>
        <SectionHeader>Score Distribution</SectionHeader>
        <Histogram data={scoreHist} barColor="var(--accent)" />
      </div>

      {/* Factor averages with weights */}
      <div>
        <SectionHeader>Factor Averages &amp; Weights</SectionHeader>
        <div className="space-y-1">
          {factorAvgs.map((f) => (
            <MiniBar
              key={f.key}
              label={`${f.label} (${(f.weight * 100).toFixed(0)}%)`}
              value={f.avg}
              max={100}
            />
          ))}
        </div>
      </div>

      <SectionHeader>Top Scored Stocks</SectionHeader>
      <div className="max-h-72 overflow-y-auto rounded-md border border-[var(--border-subtle)]">
        <StockTable
          stocks={topScored}
          columns={columns}
          selectedSymbol={selectedSym}
          onSelect={(s) => setSelectedSym(s.symbol)}
          sortKey={sortKey}
          sortDir={sortDir}
          onSort={handleSort}
        />
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   L6 — Ranking
   ═══════════════════════════════════════════════════════ */
function L6View({ stocks, ctx: _ctx }: { stocks: SymbolFactorBreakdown[]; ctx: MarketContextFrame }) {
  const all = useAllStocks(stocks);
  const [sortKey, setSortKey] = useState<string | undefined>();
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const mov = { NEW: 0, UP: 0, DOWN: 0, STABLE: 0 } as Record<string, number>;
  all.forEach((s) => {
    const rm = s.l6_ranking.rank_movement;
    mov[rm] = (mov[rm] ?? 0) + 1;
  });

  const sectorConc = useMemo(
    () =>
      SECTORS.map((s) => ({
        label: s.name.slice(0, 4),
        value: all.filter((st) => st.l4_sector.sector_id === s.id).length,
      })).filter((s) => s.value > 0),
    [all],
  );

  const columns: StockColumn[] = useMemo(
    () => [
      { key: 'symbol', label: 'Symbol', render: (s) => <span className="font-semibold">{s.symbol}</span>, sortable: true, sortValue: (s) => s.symbol },
      { key: 'sector', label: 'Sector', render: (s) => <span className="text-[var(--text-secondary)]">{s.l4_sector.sector_name}</span> },
      { key: 'dir', label: 'Dir', render: (s) => <span style={{ color: s.direction === 'LONG' ? 'var(--trade-long)' : 'var(--trade-short)' }}>{s.direction === 'LONG' ? 'L' : 'S'}</span> },
      { key: 'score', label: 'Score', sortable: true, sortValue: (s) => s.l5_scores.total, align: 'right', render: (s) => <span className="font-bold">{s.l5_scores.total.toFixed(1)}</span> },
      { key: 'dscore', label: 'ΔScore', sortable: true, sortValue: (s) => s.l6_ranking.score_change, align: 'right', render: (s) => <span style={{ color: s.l6_ranking.score_change > 0 ? 'var(--trade-long)' : s.l6_ranking.score_change < 0 ? 'var(--trade-short)' : 'var(--text-tertiary)' }}>{s.l6_ranking.score_change >= 0 ? '+' : ''}{s.l6_ranking.score_change.toFixed(2)}</span> },
      {
        key: 'movement',
        label: 'Move',
        render: (s) => {
          const rm = s.l6_ranking.rank_movement;
          const c = rm === 'NEW' ? 'var(--accent)' : rm === 'UP' ? 'var(--trade-long)' : rm === 'DOWN' ? 'var(--trade-short)' : 'var(--text-tertiary)';
          return <span className="font-bold text-[10px]" style={{ color: c }}>{rm}</span>;
        },
      },
    ],
    [],
  );

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <StatTile label="New" value={mov.NEW} borderColor="var(--accent)" valueColor="var(--accent)" />
        <StatTile label="Up" value={mov.UP} borderColor="var(--trade-long)" valueColor="var(--trade-long)" />
        <StatTile label="Down" value={mov.DOWN} borderColor="var(--trade-short)" valueColor="var(--trade-short)" />
        <StatTile label="Stable" value={mov.STABLE} />
      </div>

      <div>
        <SectionHeader>Sector Concentration</SectionHeader>
        <div className="flex items-end gap-2" style={{ height: '80px' }}>
          {sectorConc.map((s) => {
            const maxC = Math.max(...sectorConc.map((x) => x.value), 1);
            const h = (s.value / maxC) * 68;
            return (
              <div key={s.label} className="flex flex-1 flex-col items-center justify-end">
                <div
                  className="w-full rounded-t-sm"
                  style={{
                    height: `${h}px`,
                    background: 'var(--accent)',
                    opacity: 0.5 + (s.value / maxC) * 0.5,
                  }}
                />
                <span className="mt-0.5 text-[8px] text-[var(--text-tertiary)]">{s.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      <SectionHeader>Rank Changes</SectionHeader>
      <div className="max-h-64 overflow-y-auto rounded-md border border-[var(--border-subtle)]">
        <StockTable
          stocks={all}
          columns={columns}
          sortKey={sortKey}
          sortDir={sortDir}
          onSort={handleSort}
        />
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   L7 — Confluence
   ═══════════════════════════════════════════════════════ */
function L7View({ stocks, ctx: _ctx }: { stocks: SymbolFactorBreakdown[]; ctx: MarketContextFrame }) {
  const all = useAllStocks(stocks);
  const [sortKey, setSortKey] = useState<string | undefined>();
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const checkLabels: Record<string, string> = {
    strong_close: 'Strong Close',
    volume_confirm: 'Volume',
    non_exhaustion: 'Non-Exh',
    htf_alignment: 'HTF Align',
    risk_distance: 'Risk Dist',
    reward_distance: 'Reward Dist',
  };

  const dist = useMemo(() => {
    const d: Record<number, number> = { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0 };
    all.forEach((s) => {
      const cs = s.l7_confluence.score;
      d[cs] = (d[cs] ?? 0) + 1;
    });
    return Object.entries(d).map(([k, v]) => ({ label: k, value: v }));
  }, [all]);

  const perCheck = useMemo(() => {
    const keys = Object.keys(checkLabels);
    return keys.map((k) => ({
      label: checkLabels[k],
      pass: all.filter((s) => s.l7_confluence.checks[k]).length,
      total: all.length,
    }));
  }, [all]);

  const columns: StockColumn[] = useMemo(
    () => [
      { key: 'symbol', label: 'Symbol', render: (s) => <span className="font-semibold">{s.symbol}</span>, sortable: true, sortValue: (s) => s.symbol },
      { key: 'dir', label: 'Dir', render: (s) => <span style={{ color: s.direction === 'LONG' ? 'var(--trade-long)' : 'var(--trade-short)' }}>{s.direction === 'LONG' ? 'L' : 'S'}</span> },
      { key: 'score', label: 'Score', sortable: true, sortValue: (s) => s.l7_confluence.score, align: 'right', render: (s) => <span className="font-bold">{s.l7_confluence.score}/6</span> },
      ...Object.entries(checkLabels).map(([k, lbl]) => ({
        key: k,
        label: lbl.slice(0, 5),
        render: (s: SymbolFactorBreakdown) => (
          <span style={{ color: s.l7_confluence.checks[k] ? 'var(--trade-long)' : 'var(--trade-short)' }}>
            {s.l7_confluence.checks[k] ? '✓' : '✗'}
          </span>
        ),
      })),
    ],
    [],
  );

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  return (
    <div className="space-y-3">
      {/* Distribution */}
      <div>
        <SectionHeader>Confluence Score Distribution</SectionHeader>
        <Histogram data={dist} barColor="var(--accent)" />
      </div>

      {/* Per-check pass rates */}
      <div>
        <SectionHeader>Per-Check Pass Rate</SectionHeader>
        <div className="space-y-1.5">
          {perCheck.map((c) => (
            <MiniBar
              key={c.label}
              label={c.label}
              value={c.pass}
              max={c.total}
              color={
                c.pass / c.total >= 0.7
                  ? 'var(--trade-long)'
                  : c.pass / c.total >= 0.4
                    ? 'var(--trade-neutral)'
                    : 'var(--trade-short)'
              }
            />
          ))}
        </div>
      </div>

      {/* Matrix */}
      <SectionHeader>Confluence Matrix</SectionHeader>
      <div className="max-h-72 overflow-y-auto rounded-md border border-[var(--border-subtle)]">
        <StockTable
          stocks={all}
          columns={columns}
          sortKey={sortKey}
          sortDir={sortDir}
          onSort={handleSort}
        />
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   L8 — Thesis
   ═══════════════════════════════════════════════════════ */
function L8View({ stocks, ctx: _ctx }: { stocks: SymbolFactorBreakdown[]; ctx: MarketContextFrame }) {
  const all = useAllStocks(stocks);

  const grades: Record<string, number> = { ATTRACTIVE: 0, MARGINAL: 0, UNATTRACTIVE: 0 };
  const tiers: Record<string, number> = {};
  const setups: Record<string, number> = {};
  all.forEach((s) => {
    const g = s.l8_thesis.grade;
    grades[g] = (grades[g] ?? 0) + 1;
    const tier = s.l8_thesis.actionability_tier;
    tiers[tier] = (tiers[tier] ?? 0) + 1;
    const lbl = setupTypeLabels[s.l8_thesis.setup_type] ?? String(s.l8_thesis.setup_type);
    setups[lbl] = (setups[lbl] ?? 0) + 1;
  });

  const setupEntries = Object.entries(setups).sort((a, b) => b[1] - a[1]);
  const maxSetupCount = Math.max(...setupEntries.map(([, v]) => v), 1);

  const theses = useMemo(
    () => all.filter((s) => s.l8_thesis.grade !== 'UNATTRACTIVE'),
    [all],
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <StatTile label="Attractive" value={grades.ATTRACTIVE} borderColor="var(--trade-long)" valueColor="var(--trade-long)" />
        <StatTile label="Marginal" value={grades.MARGINAL} borderColor="var(--trade-neutral)" valueColor="var(--trade-neutral)" />
        <StatTile label="Unattractive" value={grades.UNATTRACTIVE} borderColor="var(--text-faint)" valueColor="var(--text-tertiary)" />
      </div>

      <div className="flex flex-wrap gap-2">
        {Object.entries(tiers)
          .sort(([, a], [, b]) => b - a)
          .map(([tier, count]) => (
            <div
              key={tier}
              className="flex items-center gap-2 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/30 px-3 py-2"
            >
              <span className="text-[11px] font-medium text-[var(--text-secondary)]">{tier}</span>
              <span className="font-mono text-base font-bold tabular-nums">{count}</span>
            </div>
          ))}
      </div>

      {/* Setup distribution bars */}
      <div>
        <SectionHeader>Setup Distribution</SectionHeader>
        <div className="space-y-1">
          {setupEntries.map(([lbl, count]) => (
            <div key={lbl} className="flex items-center gap-2">
              <span className="w-28 shrink-0 text-[10px] text-[var(--text-tertiary)]">{lbl}</span>
              <div className="h-4 flex-1 overflow-hidden rounded bg-[var(--bg-surface-raised)]">
                <div
                  className="h-full rounded transition-all"
                  style={{
                    width: `${(count / maxSetupCount) * 100}%`,
                    background: 'var(--accent)',
                  }}
                />
              </div>
              <span className="w-6 text-right font-mono text-[10px] tabular-nums text-[var(--text-secondary)]">{count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Theses table */}
      {theses.length > 0 && (
        <div>
          <SectionHeader>Published Theses ({theses.length})</SectionHeader>
          <div className="max-h-64 overflow-y-auto rounded-md border border-[var(--border-subtle)]">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="border-b border-[var(--border-subtle)] text-[10px] text-[var(--text-tertiary)]">
                  <th className="px-2 py-1.5 text-left font-medium uppercase tracking-wide">Symbol</th>
                  <th className="px-2 py-1.5 text-left font-medium uppercase tracking-wide">Setup</th>
                  <th className="px-2 py-1.5 text-right font-medium uppercase tracking-wide">Trig</th>
                  <th className="px-2 py-1.5 text-right font-medium uppercase tracking-wide">Inv</th>
                  <th className="px-2 py-1.5 text-right font-medium uppercase tracking-wide">T1</th>
                  <th className="px-2 py-1.5 text-right font-medium uppercase tracking-wide">T2</th>
                  <th className="px-2 py-1.5 text-right font-medium uppercase tracking-wide">Net R:R</th>
                  <th className="px-2 py-1.5 text-center font-medium uppercase tracking-wide">Grade</th>
                  <th className="px-2 py-1.5 text-center font-medium uppercase tracking-wide">Tier</th>
                </tr>
              </thead>
              <tbody>
                {theses.map((s) => (
                  <tr key={s.symbol} className="border-b border-[var(--border-subtle)]/50 hover:bg-[var(--bg-surface-raised)]/30">
                    <td className="px-2 py-1.5 font-semibold">{s.symbol}</td>
                    <td className="px-2 py-1.5 text-[var(--text-secondary)]">{setupTypeLabels[s.l8_thesis.setup_type] ?? s.l8_thesis.setup_type}</td>
                    <td className="px-2 py-1.5 text-right font-mono tabular-nums text-[var(--trade-long)]">{s.l8_thesis.trigger.toFixed(1)}</td>
                    <td className="px-2 py-1.5 text-right font-mono tabular-nums text-[var(--trade-short)]">{s.l8_thesis.invalidation.toFixed(1)}</td>
                    <td className="px-2 py-1.5 text-right font-mono tabular-nums text-[var(--trade-neutral)]">{s.l8_thesis.t1.toFixed(1)}</td>
                    <td className="px-2 py-1.5 text-right font-mono tabular-nums text-[var(--text-secondary)]">{s.l8_thesis.t2.toFixed(1)}</td>
                    <td
                      className="px-2 py-1.5 text-right font-mono tabular-nums font-bold"
                      style={{
                        color:
                          s.l8_thesis.net_rr >= 1.5 ? 'var(--trade-long)' : s.l8_thesis.net_rr >= 1.0 ? 'var(--trade-neutral)' : 'var(--trade-short)',
                      }}
                    >
                      {s.l8_thesis.net_rr.toFixed(2)}
                    </td>
                    <td className="px-2 py-1.5 text-center">
                      <VerdictPill verdict={s.l8_thesis.grade === 'ATTRACTIVE' ? 'PASS' : 'WARN'} />
                    </td>
                    <td className="px-2 py-1.5 text-center">
                      <span
                        className="rounded px-1 py-0.5 text-[9px] font-semibold"
                        style={{
                          background:
                            s.l8_thesis.actionability_tier === 'Tradeable' ? 'var(--trade-long-dim)' : s.l8_thesis.actionability_tier === 'Constrained' ? 'var(--trade-neutral-dim)' : 'transparent',
                          color:
                            s.l8_thesis.actionability_tier === 'Tradeable' ? 'var(--trade-long)' : s.l8_thesis.actionability_tier === 'Constrained' ? 'var(--trade-neutral)' : 'var(--text-tertiary)',
                        }}
                      >
                        {s.l8_thesis.actionability_tier}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   L9 — Monitor
   ═══════════════════════════════════════════════════════ */
function L9View({ stocks, ctx: _ctx }: { stocks: SymbolFactorBreakdown[]; ctx: MarketContextFrame }) {
  const all = useAllStocks(stocks);

  const states = { PENDING: 0, TRIGGERED: 0, ACTIVE: 0, T1_HIT: 0, T2_HIT: 0, STOPPED_OUT: 0, INVALIDATED: 0, EXPIRED: 0 };
  all.forEach((s) => {
    const st = (s.l9_monitor?.state ?? 'PENDING') as keyof typeof states;
    if (states[st] !== undefined) states[st]++;
  });

  const liveTheses = useMemo(() => all.filter((s) => (s.l9_monitor?.state ?? 'PENDING') !== 'PENDING'), [all]);
  const activeTheses = useMemo(() => all.filter((s) => {
    const st = s.l9_monitor?.state ?? '';
    return st === 'ACTIVE' || st === 'TRIGGERED' || st === 'T1_HIT';
  }), [all]);

  const avgMfe = avg(liveTheses.map((s) => s.l9_monitor?.mfe_R ?? 0));
  const avgMae = avg(liveTheses.map((s) => s.l9_monitor?.mae_R ?? 0));
  const bestMfe = Math.max(...liveTheses.map((s) => s.l9_monitor?.mfe_R ?? 0), 0);
  const worstMae = Math.min(...liveTheses.map((s) => s.l9_monitor?.mae_R ?? 0), 0);

  return (
    <div className="space-y-3">
      {/* State pipeline flow */}
      <div>
        <SectionHeader>State Pipeline</SectionHeader>
        <div className="flex flex-wrap items-center gap-1 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/30 p-3">
          {Object.entries(states)
            .filter(([, count]) => count > 0)
            .map(([state, count], i, arr) => (
              <div key={state} className="flex items-center gap-1">
                <div
                  className="rounded px-2 py-1 text-[10px] font-bold"
                  style={{
                    background:
                      state === 'ACTIVE' || state === 'T1_HIT'
                        ? 'var(--trade-long-dim)'
                        : state === 'STOPPED_OUT' || state === 'INVALIDATED'
                          ? 'var(--trade-short-dim)'
                          : state === 'TRIGGERED'
                            ? 'var(--accent-dim)'
                            : 'var(--bg-surface-raised)',
                    color:
                      state === 'ACTIVE' || state === 'T1_HIT'
                        ? 'var(--trade-long)'
                        : state === 'STOPPED_OUT' || state === 'INVALIDATED'
                          ? 'var(--trade-short)'
                          : state === 'TRIGGERED'
                            ? 'var(--accent)'
                            : 'var(--text-tertiary)',
                  }}
                >
                  {state.replace('_', ' ')} <span className="font-mono">({count})</span>
                </div>
                {i < arr.length - 1 && (
                  <span className="text-[var(--text-faint)]">→</span>
                )}
              </div>
            ))}
        </div>
      </div>

      {/* MFE/MAE stats */}
      {liveTheses.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <StatTile
            label="Avg MFE"
            value={`+${avgMfe.toFixed(2)}R`}
            hint={`Best: +${bestMfe.toFixed(2)}R`}
            borderColor="var(--trade-long)"
            valueColor="var(--trade-long)"
          />
          <StatTile
            label="Avg MAE"
            value={`${avgMae.toFixed(2)}R`}
            hint={`Worst: ${worstMae.toFixed(2)}R`}
            borderColor="var(--trade-short)"
            valueColor="var(--trade-short)"
          />
          <StatTile
            label="Active"
            value={activeTheses.length}
            hint="live positions"
            borderColor="var(--accent)"
            valueColor="var(--accent)"
          />
          <StatTile
            label="Total Live"
            value={liveTheses.length}
            hint="including pending"
          />
        </div>
      )}

      {/* Live ledger */}
      {liveTheses.length > 0 && (
        <div>
          <SectionHeader>Live Shadow Ledger</SectionHeader>
          <div className="max-h-64 overflow-y-auto rounded-md border border-[var(--border-subtle)]">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="border-b border-[var(--border-subtle)] text-[10px] text-[var(--text-tertiary)]">
                  <th className="px-2 py-1.5 text-left font-medium uppercase tracking-wide">Symbol</th>
                  <th className="px-2 py-1.5 text-center font-medium uppercase tracking-wide">State</th>
                  <th className="px-2 py-1.5 text-right font-medium uppercase tracking-wide">MFE</th>
                  <th className="px-2 py-1.5 text-right font-medium uppercase tracking-wide">MAE</th>
                  <th className="px-2 py-1.5 text-right font-medium uppercase tracking-wide">Net R:R</th>
                  <th className="px-2 py-1.5 text-left font-medium uppercase tracking-wide">Setup</th>
                </tr>
              </thead>
              <tbody>
                {liveTheses.map((s) => {
                  const st = s.l9_monitor?.state ?? 'PENDING';
                  return (
                  <tr key={s.symbol} className="border-b border-[var(--border-subtle)]/50 hover:bg-[var(--bg-surface-raised)]/30">
                    <td className="px-2 py-1.5 font-semibold">{s.symbol}</td>
                    <td className="px-2 py-1.5 text-center">
                      <span
                        className="rounded px-1 py-0.5 text-[9px] font-bold uppercase tracking-wide"
                        style={{
                          background:
                            st === 'ACTIVE' ? 'var(--trade-long-dim)' :
                            st === 'T1_HIT' ? 'var(--accent-dim)' :
                            st === 'TRIGGERED' ? 'var(--trade-neutral-dim)' :
                            'var(--bg-surface-raised)',
                          color:
                            st === 'ACTIVE' ? 'var(--trade-long)' :
                            st === 'T1_HIT' ? 'var(--accent)' :
                            st === 'TRIGGERED' ? 'var(--trade-neutral)' :
                            'var(--text-tertiary)',
                        }}
                      >
                        {st === 'T1_HIT' ? 'T1' : st.slice(0, 4)}
                      </span>
                    </td>
                    <td className="px-2 py-1.5 text-right font-mono tabular-nums text-[var(--trade-long)]">
                      +{(s.l9_monitor?.mfe_R ?? 0).toFixed(2)}R
                    </td>
                    <td className="px-2 py-1.5 text-right font-mono tabular-nums text-[var(--trade-short)]">
                      {(s.l9_monitor?.mae_R ?? 0).toFixed(2)}R
                    </td>
                    <td
                      className="px-2 py-1.5 text-right font-mono tabular-nums font-bold"
                      style={{
                        color: s.l8_thesis.net_rr >= 1.5 ? 'var(--trade-long)' : s.l8_thesis.net_rr >= 1.0 ? 'var(--trade-neutral)' : 'var(--trade-short)',
                      }}
                    >
                      {s.l8_thesis.net_rr.toFixed(2)}
                    </td>
                    <td className="px-2 py-1.5 text-[var(--text-secondary)]">{setupTypeLabels[s.l8_thesis.setup_type] ?? s.l8_thesis.setup_type}</td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {liveTheses.length === 0 && (
        <div className="py-6 text-center text-[11px] text-[var(--text-tertiary)]">
          No active theses in the shadow ledger. All positions are PENDING.
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   L10 — Edge
   ═══════════════════════════════════════════════════════ */
function L10View({ stocks, ctx }: { stocks: SymbolFactorBreakdown[]; ctx: MarketContextFrame }) {
  const all = useAllStocks(stocks);

  const tiers = useMemo(() => {
    const t: Record<number, SymbolFactorBreakdown[]> = { 1: [], 2: [], 3: [], 4: [], 5: [], 6: [] };
    all.forEach((s) => {
      const et = s.l10_edge?.edge_tier ?? 6;
      if (t[et]) t[et].push(s);
    });
    return t;
  }, [all]);

  const tierMeta = [
    { tier: 1, label: 'T1 — Prime', desc: 'Highest confidence: attractive grade + high confluence' },
    { tier: 2, label: 'T2 — High Conviction', desc: 'Strong grade + good confluence' },
    { tier: 3, label: 'T3 — Above Average', desc: 'Marginal thesis with sector tailwind' },
    { tier: 4, label: 'T4 — Average', desc: 'Marginal grade, no sector edge' },
    { tier: 5, label: 'T5 — Speculative', desc: 'Low confluence, limited edge' },
    { tier: 6, label: 'T6 — Research Only', desc: 'No edge confirmed' },
  ];

  const tierHitRates = tierMeta.map((tm) => {
    const tierStocks = tiers[tm.tier] ?? [];
    const hit = tierStocks.length > 0 ? tierStocks.filter((s) => (s.l10_edge?.edge_tier ?? 6) <= 2).length / tierStocks.length : 0;
    const n = tierStocks.length;
    const ci_lo = Math.max(0, hit - 1.96 * Math.sqrt((hit * (1 - hit)) / Math.max(n, 1)));
    const ci_hi = Math.min(1, hit + 1.96 * Math.sqrt((hit * (1 - hit)) / Math.max(n, 1)));
    return { ...tm, hit, ci_lo, ci_hi, n, stocks: tierStocks };
  });

  // Setup x Regime cross-tab
  const setups = [...new Set(all.map((s) => setupTypeLabels[s.l8_thesis.setup_type] ?? String(s.l8_thesis.setup_type)))].sort();
  const crossTab = useMemo(() => {
    return setups.map((setup) => ({
      setup,
      total: all.filter((s) => (setupTypeLabels[s.l8_thesis.setup_type] ?? String(s.l8_thesis.setup_type)) === setup).length,
      avgNetRr: avg(all.filter((s) => (setupTypeLabels[s.l8_thesis.setup_type] ?? String(s.l8_thesis.setup_type)) === setup).map((s) => s.l8_thesis.net_rr)),
      tradeable: all.filter((s) => (setupTypeLabels[s.l8_thesis.setup_type] ?? String(s.l8_thesis.setup_type)) === setup && s.l8_thesis.actionability_tier === 'Tradeable').length,
    }));
  }, [all, setups]);

  return (
    <div className="space-y-3">
      {/* Tier cards */}
      <SectionHeader>Edge Tiers — Historical Hit Rate with 95% CI</SectionHeader>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {tierHitRates.map((tm) => (
          <div
            key={tm.tier}
            className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/40 p-3"
            style={{
              borderLeft: `3px solid ${
                tm.tier <= 2
                  ? 'var(--trade-long)'
                  : tm.tier <= 4
                    ? 'var(--trade-neutral)'
                    : 'var(--text-faint)'
              }`,
            }}
          >
            <div className="flex items-center justify-between">
              <span
                className="text-[12px] font-bold"
                style={{
                  color:
                    tm.tier <= 2
                      ? 'var(--trade-long)'
                      : tm.tier <= 4
                        ? 'var(--trade-neutral)'
                        : 'var(--text-tertiary)',
                }}
              >
                {tm.label}
              </span>
              <span className="font-mono text-[10px] tabular-nums text-[var(--text-faint)]">
                N={tm.n}
              </span>
            </div>
            <div className="mt-1 text-[9px] text-[var(--text-tertiary)]">{tm.desc}</div>

            {/* CI bar */}
            <div className="mt-2">
              <div className="flex items-center justify-between text-[9px]">
                <span className="text-[var(--text-tertiary)]">
                  {(tm.hit * 100).toFixed(0)}%
                </span>
                <span className="text-[var(--text-faint)]">
                  CI [{(tm.ci_lo * 100).toFixed(0)}%–{(tm.ci_hi * 100).toFixed(0)}%]
                </span>
              </div>
              <div className="relative mt-1 h-2 w-full rounded-full bg-[var(--bg-base)]">
                {/* CI range */}
                <div
                  className="absolute top-0 h-2 rounded-full"
                  style={{
                    left: `${tm.ci_lo * 100}%`,
                    right: `${100 - tm.ci_hi * 100}%`,
                    background: 'var(--accent-dim)',
                    border: '1px solid var(--accent-soft)',
                  }}
                />
                {/* Hit rate dot */}
                <div
                  className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full"
                  style={{
                    left: `${tm.hit * 100}%`,
                    background: tm.tier <= 2 ? 'var(--trade-long)' : tm.tier <= 4 ? 'var(--trade-neutral)' : 'var(--text-faint)',
                    boxShadow: tm.tier <= 2 ? '0 0 6px var(--trade-long-soft)' : 'none',
                  }}
                />
              </div>
              <div className="mt-3 flex flex-wrap gap-1">
                {tm.stocks.slice(0, 5).map((s) => (
                  <span
                    key={s.symbol}
                    className="rounded bg-[var(--bg-surface-elev)] px-1 py-0.5 text-[8px] font-medium text-[var(--text-secondary)]"
                  >
                    {s.symbol}
                  </span>
                ))}
                {tm.stocks.length > 5 && (
                  <span className="text-[8px] text-[var(--text-faint)]">+{tm.stocks.length - 5}</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Setup cross-tab */}
      <div>
        <SectionHeader>Setup x Current Regime ({ctx.regime})</SectionHeader>
        <div className="overflow-x-auto rounded-md border border-[var(--border-subtle)]">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] text-[10px] text-[var(--text-tertiary)]">
                <th className="px-2 py-1.5 text-left font-medium uppercase tracking-wide">Setup</th>
                <th className="px-2 py-1.5 text-right font-medium uppercase tracking-wide">Count</th>
                <th className="px-2 py-1.5 text-right font-medium uppercase tracking-wide">Avg Net R:R</th>
                <th className="px-2 py-1.5 text-right font-medium uppercase tracking-wide">Tradeable</th>
              </tr>
            </thead>
            <tbody>
              {crossTab.map((row) => (
                <tr key={row.setup} className="border-b border-[var(--border-subtle)]/50 hover:bg-[var(--bg-surface-raised)]/30">
                  <td className="px-2 py-1.5 text-[var(--text-secondary)]">{row.setup}</td>
                  <td className="px-2 py-1.5 text-right font-mono tabular-nums">{row.total}</td>
                  <td
                    className="px-2 py-1.5 text-right font-mono tabular-nums font-bold"
                    style={{
                      color:
                        row.avgNetRr >= 1.5 ? 'var(--trade-long)' : row.avgNetRr >= 1.0 ? 'var(--trade-neutral)' : 'var(--trade-short)',
                    }}
                  >
                    {row.avgNetRr.toFixed(2)}
                  </td>
                  <td className="px-2 py-1.5 text-right font-mono tabular-nums text-[var(--trade-long)]">
                    {row.tradeable}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ─── Layer view map ─────────────────────────────────── */
const LAYER_VIEWS: Record<
  string,
  (props: { stocks: SymbolFactorBreakdown[]; ctx: MarketContextFrame }) => JSX.Element
> = {
  L1: L1View,
  L2: L2View,
  L3: L3View,
  L4: L4View,
  L5: L5View,
  L6: L6View,
  L7: L7View,
  L8: L8View,
  L9: L9View,
  L10: L10View,
};

/* ═══════════════════════════════════════════════════════
   Main LayerInspector
   ═══════════════════════════════════════════════════════ */
interface LayerInspectorProps {
  layerKey: string;
  stocks: SymbolFactorBreakdown[];
  ctx: MarketContextFrame;
  onClose: () => void;
  onSwitchLayer: (key: string) => void;
  onSelectStock: (stock: SymbolFactorBreakdown) => void;
}

export function LayerInspector({
  layerKey,
  stocks,
  ctx,
  onClose,
  onSwitchLayer,
}: LayerInspectorProps) {
  const curIdx = LAYER_INDEX[layerKey] ?? 0;
  const meta = LAYER_META[layerKey];
  const ViewComponent = LAYER_VIEWS[layerKey];

  // Guard: if stocks are RankingEntry[] (no factor data), show ranking preview
  // instead of crashing. Same pattern as LayerJourney.tsx:545-554.
  if (!ViewComponent || !hasFactorData(stocks)) {
    const stockList = stocks as unknown as Array<{
      symbol: string; score?: number; direction?: string;
      net_rr?: number; confluence_score?: number; setup_type?: number;
      sector_name?: string; rank_movement?: string;
    }>;
    return (
      <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3">
        <div className="mb-2 text-[11px] font-semibold text-[var(--text-secondary)]">
          {meta?.label ?? layerKey} — Ranking Preview
        </div>
        <div className="mb-2 text-[9px] text-[var(--text-tertiary)]">
          Factor breakdown not available. Showing ranking data for {stockList.length} entries.
        </div>
        <div className="max-h-[400px] overflow-y-auto">
          <table className="w-full text-[10px]">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] text-[var(--text-tertiary)]">
                <th className="px-1 py-1 text-left">#</th>
                <th className="px-1 py-1 text-left">Symbol</th>
                <th className="px-1 py-1 text-right">Score</th>
                <th className="px-1 py-1 text-right">Dir</th>
                <th className="px-1 py-1 text-right">R:R</th>
                <th className="px-1 py-1 text-right">Conf</th>
              </tr>
            </thead>
            <tbody>
              {stockList.slice(0, 25).map((s, i) => (
                <tr key={s.symbol} className="border-b border-[var(--border-subtle)]/30 hover:bg-[var(--bg-surface-raised)]">
                  <td className="px-1 py-1 text-[var(--text-tertiary)]">{i + 1}</td>
                  <td className="px-1 py-1 font-medium text-[var(--text-primary)]">{s.symbol}</td>
                  <td className="px-1 py-1 text-right text-[var(--text-secondary)]">{s.score?.toFixed(1) ?? '—'}</td>
                  <td className="px-1 py-1 text-right">{s.direction ?? '—'}</td>
                  <td className="px-1 py-1 text-right text-[var(--text-secondary)]">{s.net_rr?.toFixed(2) ?? '—'}</td>
                  <td className="px-1 py-1 text-right text-[var(--text-secondary)]">{s.confluence_score ?? '—'}/6</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  const goPrev = () => {
    const prev = LAYER_ORDER[Math.max(0, curIdx - 1)];
    if (prev !== layerKey) onSwitchLayer(prev);
  };
  const goNext = () => {
    const next = LAYER_ORDER[Math.min(LAYER_ORDER.length - 1, curIdx + 1)];
    if (next !== layerKey) onSwitchLayer(next);
  };

  return (
    <div className="flex flex-col rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/40 px-3 py-2">
        <span className="rounded bg-[var(--accent-dim)] px-1.5 py-0.5 text-[10px] font-bold text-[var(--accent)]">
          {layerKey}
        </span>
        <span className="text-[11px] font-semibold text-[var(--text-primary)]">
          {meta?.name ?? ''}
        </span>
        <span className="hidden text-[9px] text-[var(--text-tertiary)] sm:block">
          {meta?.purpose ?? ''}
        </span>

        <div className="flex-1" />

        {/* Nav buttons */}
        <button
          onClick={goPrev}
          disabled={curIdx === 0}
          className="flex h-10 w-10 items-center justify-center rounded border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] text-sm text-[var(--text-secondary)] transition-colors hover:border-[var(--border-strong)] disabled:opacity-30 sm:h-6 sm:w-6 sm:text-[10px]"
          title="Previous layer"
          aria-label="Previous layer"
        >
          ←
        </button>
        <button
          onClick={goNext}
          disabled={curIdx === LAYER_ORDER.length - 1}
          className="flex h-10 w-10 items-center justify-center rounded border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] text-sm text-[var(--text-secondary)] transition-colors hover:border-[var(--border-strong)] disabled:opacity-30 sm:h-6 sm:w-6 sm:text-[10px]"
          title="Next layer"
          aria-label="Next layer"
        >
          →
        </button>
        <button
          onClick={onClose}
          className="flex h-10 w-10 items-center justify-center rounded border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] text-sm text-[var(--text-tertiary)] transition-colors hover:border-[var(--trade-short)] hover:text-[var(--trade-short)] sm:h-6 sm:w-6 sm:text-[10px]"
          title="Close"
          aria-label="Close inspector"
        >
          ✕
        </button>
      </div>

      {/* Body */}
      <div className="overflow-y-auto p-3" style={{ maxHeight: '70vh' }}>
        <ViewComponent stocks={stocks} ctx={ctx} />
      </div>
    </div>
  );
}
