import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { apiFetch } from '@/lib/apiFetch';
import { useMarketStore } from '@/stores/marketStore';
import type { EdgeTierStatsExt } from '@/stores/marketStore';

type EdgeTiersResponse = { tiers: EdgeTierStatsExt[]; promotions: number[] };

export function useEdgeTiers() {
  const setSource = useMarketStore((s) => s.setSource);
  const setEdgeTiersBulk = useMarketStore((s) => s.setEdgeTiersBulk);
  const query = useQuery({
    queryKey: ['edgeTiers'],
    queryFn: async () => apiFetch<EdgeTiersResponse>('/api/edge/tiers'),
    refetchInterval: 60000,
  });
  useEffect(() => {
    if (query.data) {
      setSource('edge/tiers', query.data.source);
      setEdgeTiersBulk(query.data.data.tiers ?? []);
    }
  }, [query.data, setSource, setEdgeTiersBulk]);
  return {
    data: query.data?.data,
    source: query.data?.source,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
