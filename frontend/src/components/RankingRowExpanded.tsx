import { useFactorBreakdown } from '@/hooks/useFactorBreakdown';
import { DetailPanel } from './DetailPanel';
import { useMarketStore } from '@/stores/marketStore';

export function RankingRowExpanded({ symbol }: { symbol: string }) {
  const { data, isLoading } = useFactorBreakdown(symbol);
  const ctx = useMarketStore((s) => s.context);

  if (isLoading) {
    return (
      <div className="animate-pulse p-4">
        <div className="h-4 w-1/3 rounded bg-[var(--bg-surface-raised)]" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-4 text-fluid-sm text-[var(--text-secondary)]">
        No factor data available for {symbol}.
      </div>
    );
  }

  return <DetailPanel stock={data} ctx={ctx ?? undefined} />;
}
