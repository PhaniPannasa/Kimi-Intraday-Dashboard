import { useQuery } from '@tanstack/react-query';
import type { SymbolFactorBreakdown } from '@/types/api';

async function fetchFactorBreakdown(symbol: string): Promise<SymbolFactorBreakdown> {
  const res = await fetch(`/api/rankings/${encodeURIComponent(symbol)}/factors`);
  if (!res.ok) throw new Error('Failed to fetch factor breakdown');
  return res.json();
}

export function useFactorBreakdown(symbol: string | null) {
  return useQuery({
    queryKey: ['factors', symbol],
    queryFn: () => fetchFactorBreakdown(symbol!),
    enabled: !!symbol,
    staleTime: 60000,
  });
}
