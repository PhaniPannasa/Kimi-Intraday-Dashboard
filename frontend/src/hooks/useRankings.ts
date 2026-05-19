import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { apiFetch } from '@/lib/apiFetch';
import { useMarketStore } from '@/stores/marketStore';
import type { RankingEntry } from '@/types/api';

export function useRankings(direction: 'long' | 'short') {
  const setSource = useMarketStore((s) => s.setSource);

  const query = useQuery({
    queryKey: ['rankings', direction],
    queryFn: async () => apiFetch<RankingEntry[]>(`/api/rankings/top25/${direction}`),
    refetchInterval: 60000,
  });

  useEffect(() => {
    if (query.data) setSource(`rankings/top25/${direction}`, query.data.source);
  }, [query.data, setSource, direction]);

  return {
    data: query.data?.data ?? [],
    source: query.data?.source,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
