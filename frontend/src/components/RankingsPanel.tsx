'use client';

import { useState, useMemo } from 'react';
import { useRankings } from '@/hooks/useRankings';
import { useMarketStore } from '@/stores/marketStore';
import { cn } from '@/lib/utils';
import { DataAgeBadge } from './DataAgeBadge';
import type { RankingEntry } from '@/types/api';
import { setupTypeLabels } from '@/types/api';

type Direction = 'LONG' | 'SHORT';

function TierBadge({ tier }: { tier: RankingEntry['actionability_tier'] }) {
  const styles = {
    Tradeable: 'bg-[var(--trade-long-dim)] text-[var(--trade-long)]',
    Constrained: 'bg-[var(--trade-neutral-dim)] text-[var(--trade-neutral)]',
    'Research-Only': 'bg-[var(--bg-surface-raised)] text-[var(--text-tertiary)]',
  };
  return (
    <span
      className={cn(
        'inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold',
        styles[tier]
      )}
    >
      {tier === 'Research-Only' ? 'R&D' : tier}
    </span>
  );
}

function MovementIcon({ movement }: { movement: RankingEntry['rank_movement'] }) {
  const config = {
    NEW: { label: 'NEW', color: 'text-[var(--accent)]' },
    UP: { label: '▲', color: 'text-[var(--trade-long)]' },
    DOWN: { label: '▼', color: 'text-[var(--trade-short)]' },
    STABLE: { label: '—', color: 'text-[var(--text-tertiary)]' },
  };
  const c = config[movement];
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

interface RankingsPanelProps {
  onSelectSymbol?: (symbol: string) => void;
  flashedSymbols?: Map<string, string>;
}

interface MobileRankCardProps {
  entry: RankingEntry;
  rank: number;
  selected: boolean;
  onSelect: () => void;
  flash?: string;
}

function MobileRankCard({ entry, rank, selected, onSelect, flash }: MobileRankCardProps) {
  const dirColor = 'var(--trade-long)';

  return (
    <button
      onClick={onSelect}
      className={cn(
        'w-full animate-pulse rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-2 text-left',
        'border-l-[3px] transition-colors',
        flash || '',
        selected && 'border-l-[var(--accent)] bg-[var(--bg-surface-raised)]'
      )}
      style={{ borderLeftColor: dirColor }}
    >
      <div className="flex items-center gap-2">
        <span className="font-mono text-[10px] text-[var(--text-tertiary)]">{rank}</span>
        <span className="font-bold text-sm">{entry.symbol}</span>
        <MovementIcon movement={entry.rank_movement} />
        <span className="flex-1" />
        <span className="font-mono text-sm tabular-nums">{entry.score.toFixed(1)}</span>
        <span
          className={cn(
            'font-mono text-[10px]',
            entry.net_rr >= 1.1 ? 'text-[var(--trade-long)]' : 'text-[var(--text-secondary)]'
          )}
        >
          {entry.net_rr >= 0 ? '+' : ''}{entry.net_rr.toFixed(2)}%
        </span>
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-2">
        <ScoreBar score={entry.score} direction="LONG" />
        <span className="text-[10px] text-[var(--text-secondary)]">
          {setupTypeLabels[entry.setup_type] ?? entry.setup_type}
        </span>
        <span className="font-mono text-[10px] text-[var(--text-secondary)]">
          R:R {entry.net_rr.toFixed(2)}
        </span>
        <TierBadge tier={entry.actionability_tier} />
      </div>
    </button>
  );
}

export function RankingsPanel({ onSelectSymbol, flashedSymbols = new Map() }: RankingsPanelProps) {
  const [direction, setDirection] = useState<'LONG' | 'SHORT'>('LONG');
  const rankingTs = useMarketStore((s) => s.lastWSTimestamps['L6_RANKINGS']);

  const { data: longsData, isLoading: longsLoading } = useRankings('long');
  const { data: shortsData, isLoading: shortsLoading } = useRankings('short');

  const entries = direction === 'LONG' ? longsData ?? [] : shortsData ?? [];
  const isLoading = direction === 'LONG' ? longsLoading : shortsLoading;

  // Concentration metrics (L6)
  const sectorCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    entries.forEach((e) => {
      counts[e.symbol] = (counts[e.symbol] || 0) + 1;
    });
    return counts;
  }, [entries]);

  const topSectorCount = Math.max(0, ...Object.values(sectorCounts));
  const themeDay = topSectorCount >= 6;
  const scoreSpread = entries.length >= 2 ? entries[0].score - entries[entries.length - 1].score : 0;
  const strongConviction = scoreSpread > 20;

  const handleSelect = (entry: RankingEntry) => {
    onSelectSymbol?.(entry.symbol);
  };

  const accentColor = direction === 'LONG' ? 'var(--trade-long)' : 'var(--trade-short)';
  const accentDim = direction === 'LONG' ? 'var(--trade-long-dim)' : 'var(--trade-short-dim)';

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
          {themeDay ? '⚑ ' : ''}sec {topSectorCount}
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
            No {direction.toLowerCase()} candidates
          </div>
        ) : (
          <>
            {/* Mobile cards */}
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

            {/* Desktop table */}
            <div className="hidden md:block">
              <table className="w-full text-left text-[12px]">
                <thead>
                  <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[9px] uppercase tracking-wide text-[var(--text-tertiary)]">
                    <th className="px-2 py-1.5 font-medium">#</th>
                    <th className="px-2 py-1.5 font-medium">Symbol</th>
                    <th className="px-2 py-1.5 font-medium text-right">Score</th>
                    <th className="px-2 py-1.5 font-medium">Setup</th>
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
                      </td>
                      <td className="px-2 py-1.5 text-right">
                        <ScoreBar score={entry.score} direction={direction} />
                      </td>
                      <td className="px-2 py-1.5 text-[var(--text-secondary)]">
                        {setupTypeLabels[entry.setup_type] ?? entry.setup_type}
                      </td>
                      <td className="px-2 py-1.5">
                        <span className="font-mono text-[10px]">
                          {entry.confluence_score}
                          <span className="text-[var(--text-tertiary)]">/6</span>
                        </span>
                      </td>
                      <td
                        className="font-mono tabular-nums"
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