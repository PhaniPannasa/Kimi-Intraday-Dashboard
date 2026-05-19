import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { apiFetch } from '@/lib/apiFetch';
import { useMarketStore } from '@/stores/marketStore';

type FunnelCountsResponse = Record<string, { in_count: number; out_count: number; layer: string }>;

export function useFunnelCounts() {
  const setSource = useMarketStore((s) => s.setSource);
  const query = useQuery({
    queryKey: ['funnelCounts'],
    queryFn: async () => apiFetch<FunnelCountsResponse>('/api/funnel/counts'),
    refetchInterval: 30000,
  });
  useEffect(() => {
    if (query.data) setSource('funnel/counts', query.data.source);
  }, [query.data, setSource]);
  return {
    data: query.data?.data,
    source: query.data?.source,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
