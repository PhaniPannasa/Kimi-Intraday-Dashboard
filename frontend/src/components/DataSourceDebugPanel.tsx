import { useState } from 'react';
import { useTelemetry } from '@/hooks/useTelemetry';

interface Props {
  defaultOpen?: boolean;
}

export function DataSourceDebugPanel({ defaultOpen = false }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const { data } = useTelemetry();

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed right-3 top-3 z-50 rounded bg-[var(--bg-surface-raised)] px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
      >
        Truth
      </button>
    );
  }

  return (
    <div className="fixed right-3 top-3 z-50 w-72 rounded border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3 text-[11px] shadow-xl">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-bold uppercase tracking-wider">Truth</span>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)]"
        >
          ×
        </button>
      </div>
      {!data ? (
        <div className="text-[var(--text-tertiary)]">Loading telemetry…</div>
      ) : (
        <>
          <div className="mb-3">
            <div className="mb-1 text-[10px] uppercase text-[var(--text-tertiary)]">Pipeline</div>
            <div>phase: <span className="font-mono">{data.pipeline.phase}</span></div>
            <div>last_cycle_at: <span className="font-mono">{data.pipeline.last_cycle_at ?? '—'}</span></div>
            <div>last_bar_at: <span className="font-mono">{data.pipeline.last_bar_at ?? '—'}</span></div>
            <div>symbols_feeding: <span className="font-mono">{data.pipeline.symbols_feeding}</span></div>
            <div>ws_connections: <span className="font-mono">{data.pipeline.ws_connections}</span></div>
          </div>
          <div className="mb-3">
            <div className="mb-1 text-[10px] uppercase text-[var(--text-tertiary)]">Endpoints</div>
            <ul className="space-y-0.5">
              {Object.entries(data.endpoints).map(([path, src]) => (
                <li key={path} className="flex items-center justify-between">
                  <span className="font-mono text-[10px]">{path}</span>
                  <span className={src === 'pipeline' ? 'text-[var(--trade-long)]' : 'text-[var(--trade-neutral)]'}>
                    {src}
                  </span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div className="mb-1 text-[10px] uppercase text-[var(--text-tertiary)]">Layers</div>
            <div className="grid grid-cols-5 gap-1">
              {Object.entries(data.layers).map(([k, real]) => (
                <span
                  key={k}
                  className={`rounded px-1 py-0.5 text-center font-mono text-[9px] ${
                    real ? 'bg-[var(--trade-long-dim)] text-[var(--trade-long)]' : 'bg-[var(--trade-short-dim)] text-[var(--trade-short)]'
                  }`}
                >
                  {k.replace('_real', '').toUpperCase()}
                </span>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
