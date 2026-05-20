import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/lib/apiFetch';
import { useMarketStore } from '@/stores/marketStore';
import type { RankingEntry } from '@/types/api';

export function useRankingsAll() {
  const setSource = useMarketStore((s) => s.setSource);
  const setRankings = useMarketStore((s) => s.setRankings);

  const longQuery = useQuery({
    queryKey: ['rankings', 'long'],
    queryFn: async () => apiFetch<RankingEntry[]>(`/api/rankings/top25/long`),
    refetchInterval: 60000,
  });

  const shortQuery = useQuery({
    queryKey: ['rankings', 'short'],
    queryFn: async () => apiFetch<RankingEntry[]>(`/api/rankings/top25/short`),
    refetchInterval: 60000,
  });

  useEffect(() => {
    if (longQuery.data && shortQuery.data) {
      setSource('rankings/top25/long', longQuery.data.source);
      setSource('rankings/top25/short', shortQuery.data.source);
      setRankings(longQuery.data.data ?? [], shortQuery.data.data ?? []);
    }
  }, [longQuery.data, shortQuery.data, setSource, setRankings]);

  return {
    longs: longQuery.data?.data ?? [],
    shorts: shortQuery.data?.data ?? [],
    isLoading: longQuery.isLoading || shortQuery.isLoading,
    isError: longQuery.isError || shortQuery.isError,
  };
}
