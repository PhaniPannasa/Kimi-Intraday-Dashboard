import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { apiFetch } from '@/lib/apiFetch';
import { useMarketStore } from '@/stores/marketStore';
import type { CandleResponse } from '@/types/api';

export function useCandles(symbol: string) {
  const setSource = useMarketStore((s) => s.setSource);
  const query = useQuery({
    queryKey: ['candles', symbol],
    queryFn: async () => apiFetch<CandleResponse>(`/api/market/candles/${symbol}`),
    refetchInterval: 60000,
    enabled: !!symbol,
  });
  useEffect(() => {
    if (query.data) setSource('market/candles', query.data.source);
  }, [query.data, setSource]);
  return {
    data: query.data?.data,
    source: query.data?.source,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
