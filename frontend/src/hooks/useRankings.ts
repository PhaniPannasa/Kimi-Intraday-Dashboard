import { useQuery } from '@tanstack/react-query';
import type { RankingEntry } from '@/types/api';

async function fetchRankings(direction: 'long' | 'short'): Promise<RankingEntry[]> {
  const res = await fetch(`http://localhost:8084/rankings/top25/${direction}`);
  if (!res.ok) throw new Error('Failed to fetch rankings');
  return res.json();
}

export function useRankings(direction: 'long' | 'short') {
  return useQuery({
    queryKey: ['rankings', direction],
    queryFn: () => fetchRankings(direction),
    refetchInterval: 60000,
  });
}
