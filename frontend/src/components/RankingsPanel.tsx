'use client';

import { useState, useMemo } from 'react';
import { useRankings } from '@/hooks/useRankings';
import { useMarketStore } from '@/stores/marketStore';
import { cn } from '@/lib/utils';
import { DataAgeBadge } from './DataAgeBadge';
import { MockBadge } from './MockBadge';
import type { RankingEntry } from '@/types/api';
import { setupTypeLabels } from '@/types/api';

type Direction = 'LONG' | 'SHORT';

// ─── Small sub-components (kept identical in behaviour) ───

function TierBadge({ tier }: { tier: string }) {
  const styles: Record<string, string> = {
    Tradeable: 'bg-[var(--trade-long-dim)] text-[var(--trade-long)]',
    Constrained: 'bg-[var(--trade-neutral-dim)] text-[var(--trade-neutral)]',
    'Research-Only': 'bg-[var(--bg-surface-raised)] text-[var(--text-tertiary)]',
  };
  return (
    <span
      className={cn(
        'inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold',
        styles[tier] ?? styles['Research-Only']
      )}
    >
      {tier === 'Research-Only' ? 'R&D' : tier}
    </span>
  );
}

function MovementIcon({ movement }: { movement: string }) {
  const config: Record<string, { label: string; color: string }> = {
    NEW: { label: 'NEW', color: 'text-[var(--accent)]' },
    UP: { label: '▲', color: 'text-[var(--trade-long)]' },
    DOWN: { label: '▼', color: 'text-[var(--trade-short)]' },
    STABLE: { label: '—', color: 'text-[var(--text-tertiary)]' },
  };
  const c = config[movement] ?? config.STABLE;
  return <span className={cn('font-mono text-[10px] font-bold', c.color)}>{c.label}</span>;
}

function ScoreBar({ score, direction }: { score: number; direction: 'LONG' | 'SHORT' }) {
  const color = direction === 'LONG' ? 'var(--trade-long)' : 'var(--trade-short)';
  const soft = direction === 'LONG' ? 'var(--trade-long-soft)' : 'var(--trade-short-soft)';
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1 w-12 overflow-hidden rounded-full bg-[var(--bg-surface-raised)]">
        <div
          className="h-full rounded-full"
          style={{
            width: `${score}%`,
            background: `linear-gradient(90deg, ${soft} 0%, ${color} 100%)`,
          }}
        />
      </div>
      <span className="font-mono text-[11px] font-semibold tabular-nums">{score.toFixed(1)}</span>
    </div>
  );
}

// ─── Sparkline (new) ───

function SparklineCol({ data, direction }: { data: number[]; direction: 'LONG' | 'SHORT' }) {
  if (!data || data.length < 2) return null;
  const w = 30;
  const h = 16;
  const mn = Math.min(...data);
  const mx = Math.max(...data);
  const rng = mx - mn || 1;
  const pts = data
    .map((v, i) => `${((i / (data.length - 1)) * w).toFixed(1)},${(h - ((v - mn) / rng) * h).toFixed(1)}`)
    .join(' ');
  const color = direction === 'LONG' ? 'var(--trade-long)' : 'var(--trade-short)';
  return (
    <svg width={w} height={h} className="inline-block overflow-visible align-middle" aria-hidden="true">
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ─── Common display-row type & normaliser ───

interface DisplayRow {
  symbol: string;
  score: number;
  direction: 'LONG' | 'SHORT';
  rank_movement: string;
  net_rr: number;
  confluence_score: number;
  setup_type: number;
  actionability_tier: string;
  // Optional rich fields — undefined when not available from API
  price?: number;
  change_pct?: number;
  sector_name?: string;
  setup_label?: string;
  spark?: number[];
}

function toDisplayRow(e: RankingEntry): DisplayRow {
  return {
    symbol: e.symbol,
    score: e.score,
    direction: e.direction,
    rank_movement: e.rank_movement,
    net_rr: e.net_rr,
    confluence_score: e.confluence_score ?? 0,
    setup_type: e.setup_type,
    actionability_tier: e.actionability_tier,
    price: e.price,
    change_pct: e.change_pct,
    sector_name: e.sector_name,
    setup_label: e.setup_label,
    spark: e.sparkline,
  };
}

// ─── Mobile card ───

interface MobileRankCardProps {
  entry: DisplayRow;
  rank: number;
  selected: boolean;
  onSelect: () => void;
  flash?: string;
}

function MobileRankCard({ entry, rank, selected, onSelect, flash }: MobileRankCardProps) {
  const dirColor = entry.direction === 'LONG' ? 'var(--trade-long)' : 'var(--trade-short)';

  return (
    <button
      onClick={onSelect}
      className={cn(
        'w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-2 text-left',
        'border-l-[3px] transition-colors',
        flash || '',
        selected && 'border-l-[var(--accent)] bg-[var(--bg-surface-raised)]'
      )}
      style={{ borderLeftColor: dirColor }}
    >
      <div className="flex items-center gap-1.5">
        <span className="font-mono text-[10px] text-[var(--text-tertiary)]">{rank}</span>
        <span className="truncate text-[13px] font-bold">{entry.symbol}</span>
        <MovementIcon movement={entry.rank_movement} />
        <span className="flex-1" />
        {entry.price != null && (
          <span className="hidden font-mono text-[11px] tabular-nums min-[380px]:inline">
            {'₹'}{entry.price.toFixed(2)}
          </span>
        )}
        <span className="font-mono text-[13px] tabular-nums">{entry.score.toFixed(1)}</span>
        <span
          className={cn(
            'font-mono text-[10px]',
            entry.net_rr >= 1.1 ? 'text-[var(--trade-long)]' : 'text-[var(--text-secondary)]'
          )}
        >
          {entry.net_rr >= 0 ? '+' : ''}{entry.net_rr.toFixed(2)}
        </span>
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-2">
        {entry.spark && <SparklineCol data={entry.spark} direction={entry.direction} />}
        <ScoreBar score={entry.score} direction={entry.direction} />
        <span className="text-[10px] text-[var(--text-secondary)]">
          {entry.setup_label || (setupTypeLabels[entry.setup_type] ?? entry.setup_type)}
        </span>
        {/* Sector on mobile */}
        {entry.sector_name && (
          <span className="text-[9px] text-[var(--text-tertiary)]">{entry.sector_name}</span>
        )}
        <span className="font-mono text-[10px] text-[var(--text-secondary)]">
          R:R {entry.net_rr.toFixed(2)}
        </span>
        <TierBadge tier={entry.actionability_tier} />
      </div>
    </button>
  );
}

// ─── Props ───

interface RankingsPanelProps {
  onSelectSymbol?: (symbol: string) => void;
  flashedSymbols?: Map<string, string>;
  /** When provided, use these entries instead of the API hook. */
  entries?: RankingEntry[];
}

// ─── Component ───

export function RankingsPanel({ onSelectSymbol, flashedSymbols = new Map(), entries: simEntries }: RankingsPanelProps) {
  const [direction, setDirection] = useState<'LONG' | 'SHORT'>('LONG');
  const rankingTs = useMarketStore((s) => s.lastWSTimestamps['L6_RANKINGS']);
  const source = useMarketStore((s) => s.sources['rankings/top25/' + direction.toLowerCase()]);

  // API hook (always called — does nothing when simEntries are provided because we pass the other direction below)
  const { data: longsData, isLoading: longsLoading } = useRankings('long');
  const { data: shortsData, isLoading: shortsLoading } = useRankings('short');

  // Pick source
  const apiEntries: RankingEntry[] = direction === 'LONG' ? (longsData ?? []) : (shortsData ?? []);
  const simFiltered = useMemo<RankingEntry[] | null>(() => {
    if (!simEntries) return null;
    return simEntries.filter((s) => s.direction === direction);
  }, [simEntries, direction]);

  const rawEntries = simFiltered ?? apiEntries;
  const isLoading = simEntries ? false : (direction === 'LONG' ? longsLoading : shortsLoading);

  // Normalise to display rows (one-time cost per source change)
  const entries = useMemo(() => rawEntries.map(toDisplayRow), [rawEntries]);
  const hasRichData = simEntries !== undefined;

  // Sector concentration (fixed to key on sector_name when available)
  const sectorCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    entries.forEach((e) => {
      const sec = e.sector_name || e.symbol;
      counts[sec] = (counts[sec] || 0) + 1;
    });
    return counts;
  }, [entries]);

  const topSectorCount = Math.max(0, ...Object.values(sectorCounts));
  const themeDay = topSectorCount >= 6;
  const scoreSpread = entries.length >= 2 ? entries[0].score - entries[entries.length - 1].score : 0;
  const strongConviction = scoreSpread > 20;

  const handleSelect = (entry: DisplayRow) => {
    onSelectSymbol?.(entry.symbol);
  };

  const accentColor = direction === 'LONG' ? 'var(--trade-long)' : 'var(--trade-short)';
  const accentDim = direction === 'LONG' ? 'var(--trade-long-dim)' : 'var(--trade-short-dim)';

  // Column helper — only show extra columns when rich data is present
  const showChart = hasRichData;
  const showLtp = hasRichData;
  const showSector = hasRichData;

  return (
    <div
      className="flex flex-col overflow-hidden rounded-lg border-t-2 border-[var(--border-subtle)] bg-[var(--bg-surface)]"
      style={{ borderTopColor: accentColor }}
    >
      {/* Header with tabs */}
      <div
        className="flex items-center gap-2 border-b border-[var(--border-subtle)] px-3 py-2"
        style={{ background: accentDim }}
      >
        <span
          className="inline-block h-1.5 w-1.5 rounded-full"
          style={{ background: accentColor }}
        />
        <h2 className="text-sm font-bold" style={{ color: accentColor }}>
          TOP 25 {direction}
        </h2>
        <MockBadge source={source} />
        <span className="flex-1" />

        {/* Concentration metrics */}
        <span
          title="Score spread between rank 1 and 25 — wider = stronger conviction"
          className="hidden rounded px-1.5 py-0.5 font-mono text-[9px] sm:inline"
          style={{
            background: 'var(--bg-base)',
            color: strongConviction ? 'var(--trade-long)' : 'var(--text-tertiary)',
          }}
        >
          spread {scoreSpread.toFixed(1)}
        </span>
        <span
          className="hidden rounded px-1.5 py-0.5 font-mono text-[9px] sm:inline"
          style={{
            background: 'var(--bg-base)',
            color: themeDay ? 'var(--trade-neutral)' : 'var(--text-tertiary)',
          }}
        >
          {themeDay ? '⚑' : ''}sec {topSectorCount}
        </span>

        <span className="text-[10px] text-[var(--text-tertiary)]">L6</span>
        <span className="rounded bg-[var(--bg-base)] px-1.5 py-0.5 font-mono text-[10px]">
          {entries.length}
        </span>
        <DataAgeBadge timestamp={rankingTs} />
      </div>

      {/* Direction toggle */}
      <div className="flex gap-1 border-b border-[var(--border-subtle)] px-3 py-2">
        {(['LONG', 'SHORT'] as Direction[]).map((d) => (
          <button
            key={d}
            onClick={() => setDirection(d)}
            className="flex-1 rounded px-3 py-1.5 text-[11px] font-bold tracking-wide transition-colors"
            style={{
              color:
                direction === d
                  ? d === 'LONG'
                    ? 'var(--trade-long)'
                    : 'var(--trade-short)'
                  : 'var(--text-tertiary)',
              background: direction === d ? 'var(--bg-surface)' : 'transparent',
              border: `1px solid ${
                direction === d
                  ? d === 'LONG'
                    ? 'var(--trade-long-soft)'
                    : 'var(--trade-short-soft)'
                  : 'var(--border-subtle)'
              }`,
            }}
          >
            TOP 25 {d}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="p-6 text-center text-sm text-[var(--text-secondary)]">Loading…</div>
        ) : entries.length === 0 ? (
          <div className="p-6 text-center text-sm text-[var(--text-secondary)]">
            No rankings yet — pipeline idle
          </div>
        ) : (
          <>
            {/* ─── Mobile cards ─── */}
            <div className="space-y-2 p-2 md:hidden">
              {entries.map((entry, i) => (
                <MobileRankCard
                  key={entry.symbol}
                  entry={entry}
                  rank={i + 1}
                  selected={false}
                  onSelect={() => handleSelect(entry)}
                  flash={flashedSymbols.get(entry.symbol)}
                />
              ))}
            </div>

            {/* ─── Desktop table ─── */}
            <div className="hidden md:block">
              <table className="w-full text-left text-[12px]">
                <thead>
                  <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[9px] uppercase tracking-wide text-[var(--text-tertiary)]">
                    <th className="px-2 py-1.5 font-medium">#</th>
                    <th className="px-2 py-1.5 font-medium">Symbol</th>
                    {showChart && <th className="px-2 py-1.5 font-medium">Chart</th>}
                    {showLtp && <th className="px-2 py-1.5 font-medium text-right">LTP</th>}
                    <th className="px-2 py-1.5 font-medium text-right">Score</th>
                    <th className="px-2 py-1.5 font-medium">Setup</th>
                    {showSector && <th className="px-2 py-1.5 font-medium">Sector</th>}
                    <th className="px-2 py-1.5 font-medium">Conf</th>
                    <th className="px-2 py-1.5 font-medium">R:R</th>
                    <th className="px-2 py-1.5 font-medium">Tier</th>
                    <th className="px-2 py-1.5 font-medium">Move</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((entry, i) => (
                    <tr
                      key={entry.symbol}
                      onClick={() => handleSelect(entry)}
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleSelect(entry); }}
                      tabIndex={0}
                      role="button"
                      aria-label={`Select ${entry.symbol} for detail view`}
                      className={cn(
                        'cursor-pointer border-b border-[var(--border-subtle)]/50 transition-colors hover:bg-[var(--bg-surface-raised)]',
                        flashedSymbols.get(entry.symbol)
                      )}
                    >
                      <td className="px-2 py-1.5 font-mono text-[var(--text-tertiary)]">{i + 1}</td>
                      <td className="px-2 py-1.5">
                        <div className="flex items-center gap-1.5">
                          <span className="font-semibold">{entry.symbol}</span>
                          <MovementIcon movement={entry.rank_movement} />
                        </div>
                        {entry.sector_name && (
                          <div className="text-[9px] leading-tight text-[var(--text-tertiary)]">{entry.sector_name}</div>
                        )}
                      </td>
                      {showChart && (
                        <td className="px-2 py-1.5">
                          {entry.spark && <SparklineCol data={entry.spark} direction={entry.direction} />}
                        </td>
                      )}
                      {showLtp && (
                        <td className="px-2 py-1.5 text-right">
                          {entry.price != null && (
                            <div>
                              <div className="font-mono text-[11px] tabular-nums">
                                {'₹'}{entry.price.toFixed(2)}
                              </div>
                              {entry.change_pct != null && (
                                <div
                                  className="font-mono text-[10px] tabular-nums"
                                  style={{
                                    color: entry.change_pct >= 0 ? 'var(--trade-long)' : 'var(--trade-short)',
                                  }}
                                >
                                  {entry.change_pct >= 0 ? '+' : ''}{entry.change_pct.toFixed(2)}%
                                </div>
                              )}
                            </div>
                          )}
                        </td>
                      )}
                      <td className="px-2 py-1.5 text-right">
                        <ScoreBar score={entry.score} direction={entry.direction} />
                      </td>
                      <td className="px-2 py-1.5 text-[var(--text-secondary)]">
                        {entry.setup_label || (setupTypeLabels[entry.setup_type] ?? entry.setup_type)}
                      </td>
                      {showSector && (
                        <td className="px-2 py-1.5 text-[10px] text-[var(--text-tertiary)]">
                          {entry.sector_name || '—'}
                        </td>
                      )}
                      <td className="px-2 py-1.5">
                        <span className="font-mono text-[10px]">
                          {entry.confluence_score}
                          <span className="text-[var(--text-tertiary)]">/6</span>
                        </span>
                      </td>
                      <td
                        className="px-2 py-1.5 font-mono tabular-nums"
                        style={{
                          color: entry.net_rr >= 1.1 ? 'var(--trade-long)' : 'var(--text-primary)',
                        }}
                      >
                        {entry.net_rr.toFixed(2)}
                      </td>
                      <td className="px-2 py-1.5">
                        <TierBadge tier={entry.actionability_tier} />
                      </td>
                      <td className="px-2 py-1.5">
                        <MovementIcon movement={entry.rank_movement} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
