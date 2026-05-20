import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/lib/apiFetch';
import { useMarketStore } from '@/stores/marketStore';
import type { RankingEntry } from '@/types/api';

export function useRankings(direction: 'long' | 'short') {
  const setSource = useMarketStore((s) => s.setSource);
  const setRankings = useMarketStore((s) => s.setRankings);

  const query = useQuery({
    queryKey: ['rankings', direction],
    queryFn: async () => apiFetch<RankingEntry[]>(`/api/rankings/top25/${direction}`),
    refetchInterval: 60000,
  });

  useEffect(() => {
    if (query.data) {
      setSource(`rankings/top25/${direction}`, query.data.source);
      if (direction === 'long') {
        setRankings(query.data.data ?? [], useMarketStore.getState().shortRankings);
      } else {
        setRankings(useMarketStore.getState().longRankings, query.data.data ?? []);
      }
    }
  }, [query.data, setSource, setRankings, direction]);

  return {
    data: query.data?.data ?? [],
    source: query.data?.source,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
