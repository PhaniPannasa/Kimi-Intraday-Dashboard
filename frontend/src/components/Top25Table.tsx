import React, { useState } from 'react';
import { useRankings } from '@/hooks/useRankings';
import { RankingRowExpanded } from './RankingRowExpanded';
import { useMarketStore } from '@/stores/marketStore';
import { cn } from '@/lib/utils';
import { DataAgeBadge } from './DataAgeBadge';
import type { RankingEntry } from '@/types/api';
import { setupTypeLabels } from '@/types/api';

function TierBadge({ tier }: { tier: RankingEntry['actionability_tier'] }) {
  const styles = {
    Tradeable: 'bg-[var(--trade-long-dim)] text-[var(--trade-long)]',
    Constrained: 'bg-[var(--trade-neutral-dim)] text-[var(--trade-neutral)]',
    'Research-Only': 'bg-[var(--bg-surface-raised)] text-[var(--text-tertiary)]',
  };
  return (
    <span
      className={cn(
        'inline-flex items-center rounded px-1.5 py-0.5 text-fluid-xs font-medium',
        styles[tier]
      )}
    >
      {tier === 'Research-Only' ? 'R&D' : tier}
    </span>
  );
}

function MovementIcon({ movement }: { movement: RankingEntry['rank_movement'] }) {
  const config = {
    NEW: { label: 'NEW', color: 'text-blue-400' },
    UP: { label: '▲', color: 'text-[var(--trade-long)]' },
    DOWN: { label: '▼', color: 'text-[var(--trade-short)]' },
    STABLE: { label: '—', color: 'text-[var(--text-tertiary)]' },
  };
  const c = config[movement];
  return <span className={cn('font-mono text-fluid-xs', c.color)}>{c.label}</span>;
}

function ScoreBar({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-[var(--bg-surface-raised)]">
        <div
          className="h-full rounded-full bg-gradient-to-r from-[var(--trade-neutral)] to-[var(--trade-long)]"
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="text-fluid-xs font-medium tabular-nums">{score.toFixed(1)}</span>
    </div>
  );
}

function MobileCard({
  entry,
  direction,
  onClick,
}: {
  entry: RankingEntry;
  direction: 'long' | 'short';
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3 text-left transition-colors',
        'active:bg-[var(--bg-surface-raised)]',
        'hover:border-[var(--border-subtle)]/80'
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'h-2 w-1 rounded-full',
              direction === 'long' ? 'bg-[var(--trade-long)]' : 'bg-[var(--trade-short)]'
            )}
          />
          <span className="text-fluid-base font-bold">{entry.symbol}</span>
        </div>
        <MovementIcon movement={entry.rank_movement} />
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <TierBadge tier={entry.actionability_tier} />
        <span className="text-fluid-xs text-[var(--text-secondary)]">
          {setupTypeLabels[entry.setup_type] ?? entry.setup_type}
        </span>
      </div>
      <div className="mt-2 grid grid-cols-3 gap-2 text-fluid-xs">
        <div>
          <div className="text-[var(--text-tertiary)]">Score</div>
          <div className="font-medium tabular-nums">{entry.score.toFixed(1)}</div>
        </div>
        <div>
          <div className="text-[var(--text-tertiary)]">Net R:R</div>
          <div className="font-medium tabular-nums">{entry.net_rr.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-[var(--text-tertiary)]">Conf</div>
          <div className="font-medium">
            {entry.confluence_score}<span className="text-[var(--text-tertiary)]">/6</span>
          </div>
        </div>
      </div>
    </button>
  );
}

export function Top25Table({ direction }: { direction: 'long' | 'short' }) {
  const { data, isLoading } = useRankings(direction);
  const theses = useMarketStore((s) => s.theses);
  const setSelectedThesis = useMarketStore((s) => s.setSelectedThesis);
  const rankingTs = useMarketStore((s) => s.lastWSTimestamps['L6_RANKINGS']);
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null);

  const toggleExpand = (symbol: string) => {
    setExpandedSymbol((prev) => (prev === symbol ? null : symbol));
  };

  const handleSelect = (entry: RankingEntry) => {
    const match = theses.find(
      (t) => t.symbol === entry.symbol && t.direction.toLowerCase() === direction
    );
    if (match) setSelectedThesis(match);
  };

  const entries = data ?? [];

  return (
    <div
      className={cn(
        'rounded-lg border bg-[var(--bg-surface)]',
        direction === 'long'
          ? 'border-[var(--trade-long)]/20'
          : 'border-[var(--trade-short)]/20'
      )}
    >
      <div
        className={cn(
          'flex items-center gap-2 border-b border-[var(--border-subtle)] px-3 py-2 md:px-4 md:py-3',
          direction === 'long'
            ? 'bg-[var(--trade-long)]/5'
            : 'bg-[var(--trade-short)]/5'
        )}
      >
        <span
          className={cn(
            'h-2 w-2 rounded-full',
            direction === 'long' ? 'bg-[var(--trade-long)]' : 'bg-[var(--trade-short)]'
          )}
        />
        <h2 className="text-fluid-base font-bold capitalize">
          Top 25 {direction}
        </h2>
        <span className="ml-auto text-fluid-xs text-[var(--text-tertiary)]">
          {entries.length} rows
        </span>
        <DataAgeBadge timestamp={rankingTs} />
      </div>

      {isLoading ? (
        <div className="p-6 text-center text-fluid-sm text-[var(--text-secondary)]">
          Loading rankings…
        </div>
      ) : entries.length === 0 ? (
        <div className="p-6 text-center text-fluid-sm text-[var(--text-secondary)]">
          No {direction} candidates
        </div>
      ) : (
        <>
          {/* Mobile card view */}
          <div className="space-y-2 p-2 md:hidden">
            {entries.map((entry) => (
              <React.Fragment key={entry.symbol}>
                <MobileCard
                  entry={entry}
                  direction={direction}
                  onClick={() => { handleSelect(entry); toggleExpand(entry.symbol); }}
                />
                {expandedSymbol === entry.symbol && (
                  <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)] p-3">
                    <RankingRowExpanded symbol={entry.symbol} />
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>

          {/* Desktop table view */}
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full text-left text-fluid-sm">
              <thead>
                <tr className="border-b border-[var(--border-subtle)] text-[var(--text-tertiary)]">
                  <th className="px-3 py-2 font-medium">Sym</th>
                  <th className="px-3 py-2 font-medium">Score</th>
                  <th className="px-3 py-2 font-medium">Setup</th>
                  <th className="px-3 py-2 font-medium">Conf</th>
                  <th className="px-3 py-2 font-medium">R:R</th>
                  <th className="px-3 py-2 font-medium">Tier</th>
                  <th className="px-3 py-2 font-medium">Move</th>
                  <th className="px-3 py-2 font-medium w-8"></th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <React.Fragment key={entry.symbol}>
                    <tr
                      onClick={() => { handleSelect(entry); toggleExpand(entry.symbol); }}
                      className={cn(
                        'cursor-pointer border-b border-[var(--border-subtle)]/50 transition-colors',
                        'hover:bg-[var(--bg-surface-raised)]',
                        expandedSymbol === entry.symbol && 'bg-[var(--bg-surface-raised)]'
                      )}
                    >
                      <td className="px-3 py-2 font-medium">{entry.symbol}</td>
                      <td className="px-3 py-2">
                        <ScoreBar score={entry.score} />
                      </td>
                      <td className="px-3 py-2 text-[var(--text-secondary)]">
                        {setupTypeLabels[entry.setup_type] ?? entry.setup_type}
                      </td>
                      <td className="px-3 py-2">
                        <span className="font-mono text-fluid-xs">
                          {entry.confluence_score}<span className="text-[var(--text-tertiary)]">/6</span>
                        </span>
                      </td>
                      <td className="px-3 py-2 font-mono tabular-nums">
                        {entry.net_rr.toFixed(2)}
                      </td>
                      <td className="px-3 py-2">
                        <TierBadge tier={entry.actionability_tier} />
                      </td>
                      <td className="px-3 py-2">
                        <MovementIcon movement={entry.rank_movement} />
                      </td>
                      <td className="px-3 py-2 text-[var(--text-tertiary)]">
                        {expandedSymbol === entry.symbol ? '▼' : '▶'}
                      </td>
                    </tr>
                    {expandedSymbol === entry.symbol && (
                      <tr>
                        <td colSpan={8} className="border-b border-[var(--border-subtle)] bg-[var(--bg-base)] p-3">
                          <RankingRowExpanded symbol={entry.symbol} />
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
