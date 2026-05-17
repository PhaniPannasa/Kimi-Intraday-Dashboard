import type { L7ConfluenceCheck } from '@/types/api';
import { cn } from '@/lib/utils';

const checkLabels: Record<string, string> = {
  strong_close: 'Strong Close',
  volume_confirm: 'Volume Confirm',
  non_exhaustion: 'Non-Exhaustion',
  htf_alignment: 'HTF Alignment',
  risk_distance: 'Risk Distance',
  reward_distance: 'Reward Distance',
};

export function ConfluenceChecklist({ data }: { data: L7ConfluenceCheck }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      {Object.entries(data.checks).map(([key, passed]) => (
        <div
          key={key}
          className={cn(
            'flex items-center gap-2 rounded-md border px-2 py-1.5 text-fluid-xs',
            passed
              ? 'border-[var(--trade-long)]/20 bg-[var(--trade-long-dim)]/30 text-[var(--trade-long)]'
              : 'border-[var(--trade-short)]/20 bg-[var(--trade-short-dim)]/30 text-[var(--trade-short)]'
          )}
        >
          <span className="font-bold">{passed ? '✓' : '✗'}</span>
          <span>{checkLabels[key] ?? key}</span>
        </div>
      ))}
    </div>
  );
}
