import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { apiFetch } from '@/lib/apiFetch';
import { useMarketStore } from '@/stores/marketStore';

export interface HealthResponse {
  status: string;
  websocket: string;
  last_bar_processed: string;
  top25_long_count: number;
  top25_short_count: number;
  active_theses: number;
  token_expires_in_days: number;
  db_connected: boolean;
  redis_connected: boolean;
  scheduler_jobs: number;
}

export function useHealth() {
  const setSource = useMarketStore((s) => s.setSource);
  const query = useQuery({
    queryKey: ['health'],
    queryFn: async () => apiFetch<HealthResponse>('/api/health'),
    refetchInterval: 10000,
  });
  useEffect(() => {
    if (query.data) setSource('health', query.data.source);
  }, [query.data, setSource]);
  return {
    data: query.data?.data,
    source: query.data?.source,
    schedulerJobs: query.data?.data?.scheduler_jobs ?? 0,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
