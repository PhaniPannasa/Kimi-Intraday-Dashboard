import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { apiFetch } from '@/lib/apiFetch';
import { useMarketStore } from '@/stores/marketStore';
import type { ActiveThesisEntry } from '@/types/api';

type ActiveThesesResponse = { theses: ActiveThesisEntry[] };

export function useActiveTheses() {
  const setSource = useMarketStore((s) => s.setSource);
  const setActiveTheses = useMarketStore((s) => s.setActiveTheses);
  const query = useQuery({
    queryKey: ['activeTheses'],
    queryFn: async () => apiFetch<ActiveThesesResponse>('/api/monitor/active-theses'),
    refetchInterval: 30000,
  });
  useEffect(() => {
    if (query.data) {
      setSource('monitor/active-theses', query.data.source);
      setActiveTheses(query.data.data.theses ?? []);
    }
  }, [query.data, setSource, setActiveTheses]);
  return {
    data: query.data?.data,
    source: query.data?.source,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
