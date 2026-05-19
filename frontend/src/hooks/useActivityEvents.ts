import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { apiFetch } from '@/lib/apiFetch';
import { useMarketStore } from '@/stores/marketStore';
import type { ActivityEvent } from '@/types/api';

type ActivityEventsResponse = { events: ActivityEvent[]; total: number };

export function useActivityEvents() {
  const setSource = useMarketStore((s) => s.setSource);
  const query = useQuery({
    queryKey: ['activityEvents'],
    queryFn: async () => apiFetch<ActivityEventsResponse>('/api/activity/events?since=0&limit=20'),
    refetchInterval: 15000,
  });
  useEffect(() => {
    if (query.data) setSource('activity/events', query.data.source);
  }, [query.data, setSource]);
  return {
    data: query.data?.data,
    source: query.data?.source,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
