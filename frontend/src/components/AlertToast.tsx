'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import { useMarketStore } from '@/stores/marketStore';
import type { SimSnapshot, SimStock } from '@/data/engineSimulator';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type AlertType =
  | 'invalidation'
  | 'triggered'
  | 't1_hit'
  | 't2_hit'
  | 'regime'
  | 'edge';

export interface Alert {
  id: string;
  type: AlertType;
  label: string;
  message: string;
  ts: string;
}

// ---------------------------------------------------------------------------
// Alert icons
// ---------------------------------------------------------------------------

function AlertIcon({ type }: { type: AlertType }) {
  const labels: Record<AlertType, string> = {
    invalidation: 'Invalidation alert',
    triggered: 'Thesis triggered alert',
    t1_hit: 'T1 target hit alert',
    t2_hit: 'T2 target hit alert',
    regime: 'Regime change alert',
    edge: 'Edge promotion alert',
  };
  const label = labels[type] ?? 'Alert';

  if (type === 'invalidation')
    return (
      <svg role="img" aria-label={label} aria-hidden="false" width="14" height="14" viewBox="0 0 14 14" className="inline-block">
        <path d="M7 1L13 12H1z" fill="currentColor" />
        <rect x="6.4" y="4.5" width="1.2" height="4" fill="var(--bg-surface)" />
        <rect x="6.4" y="9" width="1.2" height="1.2" fill="var(--bg-surface)" />
      </svg>
    );
  if (type === 'triggered')
    return (
      <svg role="img" aria-label={label} aria-hidden="false" width="14" height="14" viewBox="0 0 14 14" className="inline-block">
        <circle cx="7" cy="7" r="6" fill="none" stroke="currentColor" strokeWidth="1.4" />
        <circle cx="7" cy="7" r="2.2" fill="currentColor" />
      </svg>
    );
  if (type === 't1_hit' || type === 't2_hit')
    return (
      <svg role="img" aria-label={label} aria-hidden="false" width="14" height="14" viewBox="0 0 14 14" className="inline-block">
        <path d="M2 7l3.2 3.2L12 3.4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  if (type === 'regime')
    return (
      <svg role="img" aria-label={label} aria-hidden="false" width="14" height="14" viewBox="0 0 14 14" className="inline-block">
        <path d="M2 11L6 4l3 3.5L12 2" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="12" cy="2" r="1.2" fill="currentColor" />
      </svg>
    );
  // edge / fallback
  return (
    <svg role="img" aria-label={label} aria-hidden="false" width="14" height="14" viewBox="0 0 14 14" className="inline-block">
      <circle cx="7" cy="7" r="5.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <rect x="6.3" y="3.5" width="1.4" height="5" fill="currentColor" />
      <rect x="6.3" y="9" width="1.4" height="1.4" fill="currentColor" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Hook: useAlertFeed
// Drives alerts from a SimSnapshot (simulator mode).  Auto-dismisses after
// 8 seconds.  Returns { alerts, dismiss }.
// ---------------------------------------------------------------------------

export function useAlertFeed(snapshot: SimSnapshot, cycle: number) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const prevRef = useRef<{
    ctx: SimSnapshot['ctx'] | null;
    stocks: Map<string, SimStock>;
  }>({ ctx: null, stocks: new Map() });
  const processedRef = useRef(-1);
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(
    new Map(),
  );

  // Cleanup all timers on unmount
  useEffect(() => {
    return () => {
      for (const t of timersRef.current.values()) clearTimeout(t);
      timersRef.current.clear();
    };
  }, []);

  useEffect(() => {
    if (cycle <= processedRef.current) return;
    processedRef.current = cycle;

    const currentStocks = new Map<string, SimStock>();
    for (const s of snapshot.universe.longs) currentStocks.set(s.symbol, s);
    for (const s of snapshot.universe.shorts) currentStocks.set(s.symbol, s);

    const newAlerts: Alert[] = [];
    const now = new Date().toISOString();

    // --- Regime change ---
    if (
      prevRef.current.ctx &&
      prevRef.current.ctx.regime !== snapshot.ctx.regime
    ) {
      newAlerts.push({
        id: `regime-${cycle}-${Date.now()}`,
        type: 'regime',
        label: 'Regime',
        message: `${prevRef.current.ctx.regime} → ${snapshot.ctx.regime} (VIX ${snapshot.ctx.vix_value.toFixed(1)} ${snapshot.ctx.vix_band})`,
        ts: now,
      });
    }

    // --- State transitions & edge promotions ---
    for (const [sym, stock] of currentStocks) {
      const prev = prevRef.current.stocks.get(sym);
      if (!prev) continue;

      // PENDING → TRIGGERED
      if (prev.state === 'PENDING' && stock.state === 'TRIGGERED') {
        newAlerts.push({
          id: `trig-${sym}-${cycle}`,
          type: 'triggered',
          label: 'Triggered',
          message: `${sym} ${stock.direction} triggered at ${stock.trigger.toFixed(1)} · ${stock.setup_label} R:R ${stock.net_rr.toFixed(2)}`,
          ts: now,
        });
      }

      // → T1_HIT (from TRIGGERED or ACTIVE)
      if (
        (prev.state === 'TRIGGERED' || prev.state === 'ACTIVE') &&
        stock.state === 'T1_HIT'
      ) {
        newAlerts.push({
          id: `t1-${sym}-${cycle}`,
          type: 't1_hit',
          label: 'T1 Target',
          message: `${sym} ${stock.direction} hit T1 at ${stock.t1.toFixed(1)} · MFE +${stock.mfe_R.toFixed(2)}R`,
          ts: now,
        });
      }

      // → ACTIVE
      if (stock.state === 'ACTIVE' && prev.state !== 'ACTIVE') {
        newAlerts.push({
          id: `active-${sym}-${cycle}`,
          type: 'triggered',
          label: 'ACTIVE',
          message: `${sym} ${stock.direction} now active · MFE +${stock.mfe_R.toFixed(2)}R`,
          ts: now,
        });
      }

      // Edge promotion (tier improves to <=2)
      if (prev.edge_tier > 2 && stock.edge_tier <= 2) {
        newAlerts.push({
          id: `edge-${sym}-${cycle}`,
          type: 'edge',
          label: 'Edge ↑',
          message: `${sym} promoted to T${stock.edge_tier} (was T${prev.edge_tier}) · ${stock.setup_label}`,
          ts: now,
        });
      }

      // Big score jump (|Δ| >= 5) — neutral regime-style alert
      const scoreDiff = stock.score - prev.score;
      if (scoreDiff >= 5) {
        newAlerts.push({
          id: `jumpUp-${sym}-${cycle}`,
          type: 'regime',
          label: 'Score ↑',
          message: `${sym} score +${scoreDiff.toFixed(1)} to ${stock.score.toFixed(1)} · ${stock.direction} ${stock.setup_label}`,
          ts: now,
        });
      } else if (scoreDiff <= -5) {
        newAlerts.push({
          id: `jumpDn-${sym}-${cycle}`,
          type: 'regime',
          label: 'Score ↓',
          message: `${sym} score ${scoreDiff.toFixed(1)} to ${stock.score.toFixed(1)} · ${stock.direction} ${stock.setup_label}`,
          ts: now,
        });
      }
    }

    // --- Invalidations: stocks that were active/triggered and dropped out ---
    for (const [sym, prevStock] of prevRef.current.stocks) {
      if (
        !currentStocks.has(sym) &&
        (prevStock.state === 'ACTIVE' || prevStock.state === 'TRIGGERED')
      ) {
        newAlerts.push({
          id: `inv-${sym}-${cycle}`,
          type: 'invalidation',
          label: 'Invalidated',
          message: `${sym} dropped from top 25 · was ${prevStock.state} · MFE ${prevStock.mfe_R >= 0 ? '+' : ''}${prevStock.mfe_R.toFixed(2)}R`,
          ts: now,
        });
      }
    }

    prevRef.current = { ctx: snapshot.ctx, stocks: currentStocks };

    // Accumulate + schedule dismissals
    if (newAlerts.length > 0) {
      setAlerts((prev) => [...prev, ...newAlerts].slice(-20));
      for (const a of newAlerts) {
        const timer = setTimeout(() => {
          setAlerts((prev) => prev.filter((x) => x.id !== a.id));
          timersRef.current.delete(a.id);
        }, 8000);
        timersRef.current.set(a.id, timer);
      }
    }
  }, [snapshot, cycle]);

  const dismiss = useCallback((id: string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id));
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
  }, []);

  return { alerts, dismiss };
}

// ---------------------------------------------------------------------------
// Component: AlertToast
// Reads from the Zustand store (live WebSocket mode).
// ---------------------------------------------------------------------------

export function AlertToast() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const prevCtxRef = useRef(useMarketStore.getState().context);
  const ctx = useMarketStore((s) => s.context);
  const invalidatedTheses = useMarketStore((s) => s.invalidatedTheses);
  const edgeTiers = useMarketStore((s) => s.edgeTiers);
  const invalidatedCountRef = useRef(invalidatedTheses.length);
  const prevEdgeTiersRef = useRef<Record<number, string>>(
    useMarketStore.getState().edgeTiers,
  );
  const cycleRef = useRef(0);

  useEffect(() => {
    const newAlerts: Alert[] = [];
    const nowIso = new Date().toISOString();

    // --- Regime change ---
    if (
      prevCtxRef.current &&
      ctx &&
      prevCtxRef.current.regime !== ctx.regime
    ) {
      newAlerts.push({
        id: `regime-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        type: 'regime',
        label: 'Regime',
        message: `${prevCtxRef.current.regime} → ${ctx.regime} · VIX ${ctx.vix_value.toFixed(1)} ${ctx.vix_band}`,
        ts: nowIso,
      });
    }

    // --- Invalidations from L9 ---
    if (invalidatedTheses.length > invalidatedCountRef.current) {
      const newOnes = invalidatedTheses.slice(invalidatedCountRef.current);
      for (const inv of newOnes) {
        const symbol = inv.thesis_id.split('-')[0] || inv.thesis_id;
        newAlerts.push({
          id: `inv-${inv.thesis_id}-${Date.now()}`,
          type: 'invalidation',
          label: 'Invalidated',
          message: `${symbol}: ${inv.reason}`,
          ts: nowIso,
        });
      }
    }

    // --- Edge promotions from L10 ---
    for (const [tierStr, promotion] of Object.entries(edgeTiers)) {
      const tier = Number(tierStr);
      if (!(tier in prevEdgeTiersRef.current)) {
        newAlerts.push({
          id: `edge-${tierStr}-${Date.now()}`,
          type: 'edge',
          label: 'Edge ↑',
          message: `Tier ${tier}: ${promotion}`,
          ts: nowIso,
        });
      }
    }

    if (newAlerts.length > 0) {
      setAlerts((prev) => [...prev, ...newAlerts].slice(-20));
      for (const a of newAlerts) {
        setTimeout(() => {
          setAlerts((prev) => prev.filter((x) => x.id !== a.id));
        }, 8000);
      }
    }

    prevCtxRef.current = ctx;
    invalidatedCountRef.current = invalidatedTheses.length;
    prevEdgeTiersRef.current = edgeTiers;
    cycleRef.current += 1;
  }, [ctx, invalidatedTheses, edgeTiers]);

  const dismiss = useCallback((id: string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  }, []);

  const visible = alerts.slice(-4);
  if (visible.length === 0) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="false"
      className="fixed right-3 z-[90] flex max-w-[320px] flex-col gap-2"
      style={{ bottom: 'calc(0.75rem + env(safe-area-inset-bottom, 0px))' }}
    >
      {visible.map((a) => {
        const palette =
          (
            {
              invalidation: { c: 'var(--trade-short)', bg: 'var(--trade-short-dim)' },
              triggered: { c: 'var(--accent)', bg: 'var(--accent-dim)' },
              t1_hit: { c: 'var(--trade-long)', bg: 'var(--trade-long-dim)' },
              t2_hit: { c: 'var(--trade-long)', bg: 'var(--trade-long-dim)' },
              regime: { c: 'var(--trade-neutral)', bg: 'var(--trade-neutral-dim)' },
              edge: { c: 'var(--accent)', bg: 'var(--accent-dim)' },
            } as Record<string, { c: string; bg: string }>
          )[a.type] || { c: 'var(--text-secondary)', bg: 'var(--bg-surface-raised)' };

        const ts = new Date(a.ts).toLocaleTimeString('en-IN', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        });

        return (
          <div
            key={a.id}
            className="animate-toast-in rounded border-l-[3px] bg-[var(--bg-surface)] p-2.5 shadow-lg"
            style={{
              borderColor: palette.c,
              boxShadow: '0 6px 20px rgba(0,0,0,0.4)',
            }}
          >
            <div className="flex items-start gap-2">
              <span
                className="flex h-5 w-5 shrink-0 items-center justify-center rounded"
                style={{ background: palette.bg, color: palette.c }}
              >
                <AlertIcon type={a.type} />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline gap-1.5">
                  <span
                    className="text-[10px] font-bold uppercase tracking-wide"
                    style={{ color: palette.c }}
                  >
                    {a.label}
                  </span>
                  <span className="font-mono text-[9px] text-[var(--text-tertiary)]">
                    {ts}
                  </span>
                </div>
                <div className="mt-0.5 text-[11px] leading-tight text-[var(--text-primary)]">
                  {a.message}
                </div>
              </div>
              <button
                onClick={() => dismiss(a.id)}
                className="shrink-0 text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]"
                style={{ fontSize: 14, lineHeight: 1 }}
              >
                ×
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
