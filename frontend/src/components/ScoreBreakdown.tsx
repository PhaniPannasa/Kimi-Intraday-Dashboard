import type { L5ScoreBreakdown } from '@/types/api';
import { cn } from '@/lib/utils';

const factorLabels: Record<string, string> = {
  f1_trend: 'Trend',
  f2_momentum: 'Momentum',
  f3_volume: 'Volume',
  f4_volpos: 'Vol Position',
  f5_structure: 'Structure',
  f6_sector: 'Sector',
  f7_risk: 'Risk',
};

export function ScoreBreakdown({ scores }: { scores: L5ScoreBreakdown }) {
  const items = [
    { key: 'f1_trend', value: scores.f1_trend },
    { key: 'f2_momentum', value: scores.f2_momentum },
    { key: 'f3_volume', value: scores.f3_volume },
    { key: 'f4_volpos', value: scores.f4_volpos },
    { key: 'f5_structure', value: scores.f5_structure },
    { key: 'f6_sector', value: scores.f6_sector },
    { key: 'f7_risk', value: scores.f7_risk },
  ];

  return (
    <div className="space-y-1.5">
      {items.map(({ key, value }) => {
        const color =
          value >= 70
            ? 'bg-[var(--trade-long)]'
            : value >= 40
              ? 'bg-[var(--trade-neutral)]'
              : 'bg-[var(--trade-short)]';
        return (
          <div key={key} className="flex items-center gap-2">
            <span className="w-20 shrink-0 text-fluid-xs text-[var(--text-tertiary)]">
              {factorLabels[key]}
            </span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--bg-surface-raised)]">
              <div className={cn('h-full rounded-full', color)} style={{ width: `${value}%` }} />
            </div>
            <span className="w-8 text-right text-fluid-xs font-medium tabular-nums">{value}</span>
          </div>
        );
      })}
    </div>
  );
}
