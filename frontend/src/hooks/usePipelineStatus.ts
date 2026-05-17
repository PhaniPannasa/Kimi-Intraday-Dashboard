import { useQuery } from '@tanstack/react-query';
import type { PipelineStatusResponse } from '@/types/api';

async function fetchPipelineStatus(): Promise<PipelineStatusResponse> {
  const res = await fetch('/api/pipeline/status');
  if (!res.ok) throw new Error('Failed to fetch pipeline status');
  return res.json();
}

export function usePipelineStatus() {
  return useQuery({
    queryKey: ['pipeline', 'status'],
    queryFn: fetchPipelineStatus,
    refetchInterval: 15000,
    staleTime: 10000,
  });
}
