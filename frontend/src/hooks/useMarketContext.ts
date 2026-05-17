import { useQuery } from '@tanstack/react-query';
import type { MarketContextFrame } from '@/types/api';

async function fetchMarketContext(): Promise<MarketContextFrame> {
  const res = await fetch('/api/market/context');
  if (!res.ok) throw new Error('Failed to fetch market context');
  return res.json();
}

export function useMarketContext() {
  return useQuery({
    queryKey: ['marketContext'],
    queryFn: fetchMarketContext,
    refetchInterval: 300000,
  });
}
