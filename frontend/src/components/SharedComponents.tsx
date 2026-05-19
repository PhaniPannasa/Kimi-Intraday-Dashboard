'use client';

import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import type { SimStock } from '@/data/simTypes';
import type { ReactNode } from 'react';

/* ─── StatTile ──────────────────────────────────────── */
export function StatTile({
  label,
  value,
  hint,
  borderColor,
  valueColor,
}: {
  label: string;
  value: string | number;
  hint?: string;
  borderColor?: string;
  valueColor?: string;
}) {
  return (
    <div
      className="min-w-0 flex-1 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/40 p-2.5"
      style={borderColor ? { borderLeft: `3px solid ${borderColor}` } : undefined}
    >
      <div className="text-[10px] font-medium uppercase tracking-wide text-[var(--text-tertiary)]">
        {label}
      </div>
      <div
        className="font-mono text-lg font-bold tabular-nums"
        style={{ color: valueColor ?? 'var(--text-primary)' }}
      >
        {value}
      </div>
      {hint && <div className="text-[10px] text-[var(--text-tertiary)]">{hint}</div>}
    </div>
  );
}

/* ─── MiniBar ────────────────────────────────────────── */
export function MiniBar({
  label,
  value,
  max = 100,
  color,
  showValue = true,
  height = 4,
}: {
  label: string;
  value: number;
  max?: number;
  color?: string;
  showValue?: boolean;
  height?: number;
}) {
  const pct = Math.min(100, max > 0 ? (value / max) * 100 : 0);
  const barColor =
    color ??
    (pct >= 70 ? 'var(--trade-long)' : pct >= 40 ? 'var(--trade-neutral)' : 'var(--trade-short)');
  return (
    <div className="flex items-center gap-2">
      <span className="w-16 shrink-0 text-[10px] text-[var(--text-tertiary)]">{label}</span>
      <div className="flex-1 overflow-hidden rounded-full bg-[var(--bg-surface-raised)]" style={{ height }}>
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{ width: `${pct}%`, background: barColor }}
        />
      </div>
      {showValue && (
        <span className="w-8 text-right font-mono text-[10px] tabular-nums text-[var(--text-secondary)]">
          {value.toFixed(0)}
        </span>
      )}
    </div>
  );
}

/* ─── Histogram ──────────────────────────────────────── */
export function Histogram({
  data,
  height = 100,
  barColor,
  highlightKey,
}: {
  data: { label: string; value: number }[];
  height?: number;
  barColor?: string;
  highlightKey?: string;
}) {
  const maxVal = Math.max(...data.map((d) => d.value), 1);
  return (
    <div className="flex items-end gap-[2px]" style={{ height: `${height}px` }}>
      {data.map((d) => {
        const barH = maxVal > 0 ? Math.max(2, (d.value / maxVal) * (height - 10)) : 2;
        const isHighlight = d.label === highlightKey;
        return (
          <div key={d.label} className="flex flex-1 flex-col items-center justify-end" style={{ height: '100%' }}>
            <span className="text-[9px] leading-none text-[var(--text-tertiary)]">{d.value.toFixed(0)}</span>
            <div
              className="mt-0.5 w-full rounded-t-sm transition-all duration-200"
              style={{
                height: `${barH}px`,
                background: isHighlight ? barColor ?? 'var(--accent)' : barColor ?? 'var(--border-subtle)',
                opacity: isHighlight ? 1 : 0.55,
              }}
            />
            <span className="mt-0.5 max-w-full truncate text-[7px] text-[var(--text-tertiary)]">{d.label}</span>
          </div>
        );
      })}
    </div>
  );
}

/* ─── StockTable ──────────────────────────────────────── */
export interface StockColumn {
  key: string;
  label: string;
  render: (stock: SimStock) => ReactNode;
  sortValue?: (stock: SimStock) => number | string;
  sortable?: boolean;
  align?: 'left' | 'right';
}

export function StockTable({
  stocks,
  columns,
  selectedSymbol,
  onSelect,
  sortKey,
  sortDir,
  onSort,
}: {
  stocks: SimStock[];
  columns: StockColumn[];
  selectedSymbol?: string | null;
  onSelect?: (stock: SimStock) => void;
  sortKey?: string;
  sortDir?: 'asc' | 'desc';
  onSort?: (key: string) => void;
}) {
  const sorted = useMemo(() => {
    if (!sortKey) return stocks;
    const col = columns.find((c) => c.key === sortKey);
    if (!col) return stocks;
    return [...stocks].sort((a, b) => {
      const ra = col.sortValue ? col.sortValue(a) : col.render(a);
      const rb = col.sortValue ? col.sortValue(b) : col.render(b);
      const na = typeof ra === 'number' ? ra : parseFloat(String(ra));
      const nb = typeof rb === 'number' ? rb : parseFloat(String(rb));
      if (!isNaN(na) && !isNaN(nb)) {
        return sortDir === 'asc' ? na - nb : nb - na;
      }
      const sa = String(ra);
      const sb = String(rb);
      return sortDir === 'asc' ? sa.localeCompare(sb) : sb.localeCompare(sa);
    });
  }, [stocks, columns, sortKey, sortDir]);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[11px]">
        <thead>
          <tr className="border-b border-[var(--border-subtle)] text-[10px] text-[var(--text-tertiary)]">
            {columns.map((col) => (
              <th
                key={col.key}
                className={cn(
                  'px-2 py-1.5 font-medium uppercase tracking-wide',
                  col.sortable && 'cursor-pointer select-none hover:text-[var(--text-secondary)]',
                  col.align === 'right' && 'text-right',
                )}
                onClick={() => col.sortable && onSort?.(col.key)}
              >
                {col.label}
                {sortKey === col.key && (
                  <span className="ml-1 text-[9px]">{sortDir === 'asc' ? '▲' : '▼'}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((stock) => (
            <tr
              key={stock.symbol}
              className={cn(
                'cursor-pointer border-b border-[var(--border-subtle)]/50 transition-colors hover:bg-[var(--bg-surface-raised)]/50',
                selectedSymbol === stock.symbol && 'bg-[var(--accent-dim)]',
              )}
              onClick={() => onSelect?.(stock)}
              tabIndex={0}
              role="row"
              aria-selected={selectedSymbol === stock.symbol}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={cn(
                    'px-2 py-1.5',
                    col.align === 'right' && 'text-right font-mono tabular-nums',
                  )}
                >
                  {col.render(stock)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {sorted.length === 0 && (
        <div className="py-6 text-center text-[11px] text-[var(--text-tertiary)]">No data</div>
      )}
    </div>
  );
}

/* ─── VerdictPill ────────────────────────────────────── */
export function VerdictPill({ verdict }: { verdict: string }) {
  const color =
    verdict === 'PASS'
      ? 'var(--trade-long)'
      : verdict === 'WARN'
        ? 'var(--trade-neutral)'
        : verdict === 'FAIL'
          ? 'var(--trade-short)'
          : verdict === 'LIVE'
            ? 'var(--accent)'
            : 'var(--text-tertiary)';
  const bg =
    verdict === 'PASS'
      ? 'var(--trade-long-dim)'
      : verdict === 'WARN'
        ? 'var(--trade-neutral-dim)'
        : verdict === 'FAIL'
          ? 'var(--trade-short-dim)'
          : verdict === 'LIVE'
            ? 'var(--accent-dim)'
            : 'transparent';
  return (
    <span
      className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold tracking-wide"
      style={{ color, background: bg }}
    >
      {verdict}
    </span>
  );
}

/* ─── SectionHeader ──────────────────────────────────── */
export function SectionHeader({ children }: { children: ReactNode }) {
  return (
    <div className="mb-2 text-[11px] font-semibold text-[var(--text-secondary)] uppercase tracking-wide">
      {children}
    </div>
  );
}
