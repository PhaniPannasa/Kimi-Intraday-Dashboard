import { useFactorBreakdown } from '@/hooks/useFactorBreakdown';
import { FactorGrid } from './FactorGrid';

export function RankingRowExpanded({ symbol }: { symbol: string }) {
  const { data, isLoading } = useFactorBreakdown(symbol);

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

  return <FactorGrid data={data} />;
}
