import { useEffect, useState } from 'react';

export type Freshness = 'fresh' | 'aging' | 'stale';

export function useDataAge(isoTimestamp: string | null | undefined) {
  const [age, setAge] = useState('');
  const [freshness, setFreshness] = useState<Freshness>('fresh');

  useEffect(() => {
    if (!isoTimestamp) {
      setAge('');
      setFreshness('stale');
      return;
    }

    const update = () => {
      const diff = Date.now() - new Date(isoTimestamp).getTime();
      const seconds = Math.floor(diff / 1000);
      const minutes = Math.floor(seconds / 60);

      if (seconds < 60) {
        setAge(`Updated ${seconds}s ago`);
        setFreshness('fresh');
      } else if (minutes < 3) {
        setAge(`Updated ${minutes}m ago`);
        setFreshness('aging');
      } else {
        setAge(`Updated ${minutes}m ago`);
        setFreshness('stale');
      }
    };

    update();
    const id = setInterval(update, 5000);
    return () => clearInterval(id);
  }, [isoTimestamp]);

  return { age, freshness };
}
