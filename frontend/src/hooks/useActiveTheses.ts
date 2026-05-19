import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { apiFetch } from '@/lib/apiFetch';
import { useMarketStore } from '@/stores/marketStore';
import type { ActiveThesisEntry } from '@/types/api';

type ActiveThesesResponse = { theses: ActiveThesisEntry[] };

export function useActiveTheses() {
  const setSource = useMarketStore((s) => s.setSource);
  const query = useQuery({
    queryKey: ['activeTheses'],
    queryFn: async () => apiFetch<ActiveThesesResponse>('/api/monitor/active-theses'),
    refetchInterval: 30000,
  });
  useEffect(() => {
    if (query.data) setSource('monitor/active-theses', query.data.source);
  }, [query.data, setSource]);
  return {
    data: query.data?.data,
    source: query.data?.source,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
