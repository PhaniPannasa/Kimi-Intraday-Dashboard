import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { apiFetch } from '@/lib/apiFetch';
import { useMarketStore } from '@/stores/marketStore';
import type { MarketContextFrame } from '@/types/api';

export function useMarketContext() {
  const setSource = useMarketStore((s) => s.setSource);
  const setContext = useMarketStore((s) => s.setContext);

  const query = useQuery({
    queryKey: ['marketContext'],
    queryFn: async () => apiFetch<MarketContextFrame>('/api/market/context'),
    refetchInterval: 300000,
  });

  useEffect(() => {
    if (query.data) {
      setSource('market/context', query.data.source);
      setContext(query.data.data);
    }
  }, [query.data, setSource, setContext]);

  return {
    data: query.data?.data,
    source: query.data?.source,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
  };
}
