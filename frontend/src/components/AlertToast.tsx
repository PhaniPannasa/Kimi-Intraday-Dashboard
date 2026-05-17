import { useEffect, useState } from 'react';
import { useMarketStore } from '@/stores/marketStore';
import { cn } from '@/lib/utils';

interface Toast {
  id: string;
  message: string;
  type: 'error' | 'warn' | 'info';
}

export function AlertToast() {
  const invalidated = useMarketStore((s) => s.invalidatedTheses);
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    if (invalidated.length === 0) return;
    const latest = invalidated[invalidated.length - 1];
    const toast: Toast = {
      id: latest.thesis_id + latest.timestamp,
      message: `${latest.thesis_id}: ${latest.reason}`,
      type: 'error',
    };
    setToasts((prev) => {
      if (prev.some((t) => t.id === toast.id)) return prev;
      return [...prev, toast];
    });

    const timer = setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== toast.id));
    }, 6000);

    return () => clearTimeout(timer);
  }, [invalidated]);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2"
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={cn(
            'max-w-xs rounded-lg border px-4 py-3 shadow-lg backdrop-blur',
            toast.type === 'error'
              ? 'border-[var(--trade-short)]/30 bg-[var(--trade-short-dim)]/90 text-[var(--trade-short)]'
              : toast.type === 'warn'
                ? 'border-[var(--trade-neutral)]/30 bg-[var(--trade-neutral-dim)]/90 text-[var(--trade-neutral)]'
                : 'border-[var(--border-subtle)] bg-[var(--bg-surface)]/90 text-[var(--text-primary)]'
          )}
        >
          <div className="text-fluid-sm font-medium"
          >Invalidation
          </div>
          <div className="mt-0.5 text-fluid-xs"
          >{toast.message}
          </div>
        </div>
      ))}
    </div>
  );
}
