import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/lib/apiFetch';

export interface TelemetrySnapshot {
  timestamp: string;
  endpoints: Record<string, 'pipeline' | 'mock' | 'unknown'>;
  pipeline: {
    phase: string;
    last_cycle_at: string | null;
    last_bar_at: string | null;
    symbols_feeding: number;
    ws_connections: number;
    scheduler_running: boolean;
  };
  layers: Record<string, boolean>;
}

export function useTelemetry() {
  return useQuery({
    queryKey: ['telemetry'],
    queryFn: async () => (await apiFetch<TelemetrySnapshot>('/api/telemetry/data-sources')).data,
    refetchInterval: 5000,
  });
}
