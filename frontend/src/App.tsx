'use client';

import { useState, useEffect } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useMarketStore } from '@/stores/marketStore';
import { Header } from '@/components/Header';
import { PipelineStatusBar } from '@/components/PipelineStatusBar';
import { RegimeBanner } from '@/components/RegimeBanner';
import { RankingsPanel } from '@/components/RankingsPanel';
import { DetailPanel } from '@/components/DetailPanel';
import { ActiveMonitor } from '@/components/ActiveMonitor';
import { EdgePanel } from '@/components/EdgePanel';
import { AlertToast } from '@/components/AlertToast';

const REFRESH_BASE_MS = 60000;

function useEngine(speedMultiplier: number, paused: boolean) {
  const [cycle, setCycle] = useState(0);
  const [progress, setProgress] = useState(0);
  const [activeLayer, setActiveLayer] = useState(-1);
  const [lastCycleAt, setLastCycleAt] = useState(Date.now());
  const setWsConnected = useMarketStore((s) => s.setWsConnected);

  useEffect(() => {
    if (paused) return;
    const period = REFRESH_BASE_MS / speedMultiplier;
    const tickInterval = 200;
    let elapsed = 0;
    let isMounted = true;

    const tick = setInterval(() => {
      if (!isMounted) return;
      elapsed += tickInterval;
      const p = elapsed / period;
      if (p >= 1) {
        const newCycle = cycle + 1;
        elapsed = 0;
        setProgress(0);
        setLastCycleAt(Date.now());
        setCycle(newCycle);
        setActiveLayer(-1);
        setWsConnected(true);
      } else {
        setProgress(p);
        if (p > 0.75) {
          const phase = (p - 0.75) / 0.25;
          const layerIdx = Math.min(9, Math.floor(phase * 10));
          setActiveLayer(layerIdx);
        } else {
          setActiveLayer(-1);
        }
      }
    }, tickInterval);

    return () => {
      isMounted = false;
      clearInterval(tick);
    };
  }, [cycle, paused, speedMultiplier, setWsConnected]);

  return { cycle, progress, activeLayer, lastCycleAt };
}

function HealthStrip({ cycle, lastCycleAt }: { cycle: number; lastCycleAt: number }) {
  const items = [
    { label: 'WS', value: 'connected', color: 'var(--trade-long)' },
    { label: 'DB', value: 'timescaledb', color: 'var(--trade-long)' },
    { label: 'Cache', value: 'redis', color: 'var(--trade-long)' },
    { label: 'Sched', value: '12 jobs', color: 'var(--trade-long)' },
    { label: 'Token', value: '342d', color: 'var(--text-secondary)' },
    { label: 'Cycle', value: '2.2s', color: 'var(--text-secondary)' },
    {
      label: 'Last',
      value: lastCycleAt
        ? new Date(lastCycleAt).toLocaleTimeString('en-IN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
          })
        : '—',
      color: 'var(--text-secondary)',
    },
    { label: 'Cycle#', value: cycle, color: 'var(--text-secondary)' },
  ];

  return (
    <div
      className="flex items-center gap-3 overflow-x-auto border-t border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-1.5 text-[10px] no-scrollbar"
      style={{ whiteSpace: 'nowrap' }}
    >
      {items.map((it, i) => (
        <span key={it.label} className="flex items-center gap-1">
          {i > 0 && <span className="text-[var(--text-faint)]">·</span>}
          <span className="text-[var(--text-tertiary)]">{it.label}</span>
          <span className="font-mono font-semibold" style={{ color: it.color }}>
            {it.value}
          </span>
        </span>
      ))}
    </div>
  );
}

export default function App() {
  useWebSocket();

  const [speed] = useState(6);
  const [paused, setPaused] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [viewport, setViewport] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 1200,
    mobile: false,
  });

  const { cycle, progress, activeLayer, lastCycleAt } = useEngine(speed, paused);
  const longs = useMarketStore((s) => s.longRankings);

  useEffect(() => {
    if (!selectedSymbol && longs.length > 0) {
      setSelectedSymbol(longs[0].symbol);
    }
  }, [longs, selectedSymbol]);

  useEffect(() => {
    const onResize = () => {
      const w = window.innerWidth;
      setViewport({ width: w, mobile: w < 900 });
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const isMobile = viewport.mobile;

  return (
    <div className="flex h-[100dvh] flex-col bg-[var(--bg-base)]">
      <Header progress={progress} paused={paused} cycle={cycle} onPauseToggle={() => setPaused(!paused)} />
      <PipelineStatusBar activeLayer={activeLayer} />
      <RegimeBanner />

      {isMobile ? (
        <MobileLayout selectedSymbol={selectedSymbol} setSelectedSymbol={setSelectedSymbol} />
      ) : (
        <div className="flex flex-1 overflow-hidden p-2.5" style={{ gap: 10 }}>
          <div className="flex w-[360px] shrink-0 flex-col gap-2">
            <RankingsPanel onSelectSymbol={setSelectedSymbol} />
          </div>
          <div className="min-w-0 flex-1">
            <DetailPanel symbol={selectedSymbol || ''} />
          </div>
          <div className="flex w-[260px] shrink-0 flex-col gap-2">
            <ActiveMonitor />
            <EdgePanel />
          </div>
        </div>
      )}

      <HealthStrip cycle={cycle} lastCycleAt={lastCycleAt} />
      <AlertToast />
    </div>
  );
}

function MobileLayout({
  selectedSymbol,
  setSelectedSymbol,
}: {
  selectedSymbol: string | null;
  setSelectedSymbol: (s: string | null) => void;
}) {
  const [tab, setTab] = useState<'rankings' | 'detail' | 'theses'>('rankings');

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]">
        {[
          ['rankings', 'Top 25'],
          ['detail', 'Detail'],
          ['theses', 'Theses'],
        ].map(([k, label]) => (
          <button
            key={k}
            onClick={() => setTab(k as 'rankings' | 'detail' | 'theses')}
            className="flex-1 py-2 text-[11px] font-semibold transition-colors"
            style={{
              color: tab === k ? 'var(--text-primary)' : 'var(--text-tertiary)',
              borderBottom: `2px solid ${tab === k ? 'var(--accent)' : 'transparent'}`,
              background: tab === k ? 'var(--bg-surface-raised)' : 'transparent',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {tab === 'rankings' && <RankingsPanel onSelectSymbol={setSelectedSymbol} />}
        {tab === 'detail' && selectedSymbol && <DetailPanel symbol={selectedSymbol} />}
        {tab === 'detail' && !selectedSymbol && (
          <div className="flex h-48 items-center justify-center text-sm text-[var(--text-tertiary)]">
            Select a symbol to view details
          </div>
        )}
        {tab === 'theses' && (
          <div className="flex flex-col gap-2">
            <ActiveMonitor />
            <EdgePanel />
          </div>
        )}
      </div>
    </div>
  );
}