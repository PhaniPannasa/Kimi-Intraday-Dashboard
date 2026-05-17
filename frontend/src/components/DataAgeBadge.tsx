import { cn } from '@/lib/utils';
import { useDataAge } from '@/hooks/useDataAge';

interface DataAgeBadgeProps {
  timestamp: string | null | undefined;
}

export function DataAgeBadge({ timestamp }: DataAgeBadgeProps) {
  const { age, freshness } = useDataAge(timestamp);
  if (!age) return null;

  return (
    <span
      className={cn(
        'inline-flex items-center rounded px-1.5 py-0.5 text-fluid-xs font-medium',
        freshness === 'fresh' && 'text-[var(--text-secondary)]',
        freshness === 'aging' && 'text-[var(--trade-neutral)]',
        freshness === 'stale' && 'text-[var(--trade-short)]'
      )}
    >
      {freshness === 'stale' && (
        <span className="mr-1 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--trade-short)]" />
      )}
      {age}
    </span>
  );
}
