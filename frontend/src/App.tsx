'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useMarketStore } from '@/stores/marketStore';
import { Header } from '@/components/Header';
import { PipelineStatusBar } from '@/components/PipelineStatusBar';
import { FunnelStrip } from '@/components/FunnelStrip';
import { RegimeBanner } from '@/components/RegimeBanner';
import { RankingsPanel } from '@/components/RankingsPanel';
import { DetailPanel } from '@/components/DetailPanel';
import { LayerJourney } from '@/components/LayerJourney';
import { LayerInspector } from '@/components/LayerInspector';
import { CycleActivity, useCycleActivity } from '@/components/CycleActivity';
import { ActiveMonitor } from '@/components/ActiveMonitor';
import { EdgePanel } from '@/components/EdgePanel';
import { AlertToast, useAlertFeed } from '@/components/AlertToast';
import { HealthStrip } from '@/components/HealthStrip';
import {
  genUniverse, genMarketContext, genPipelineStatus, computeFunnel,
} from '@/data/engineSimulator';
import type { SimStock, SimSnapshot, SimMarketContext } from '@/data/engineSimulator';

const REFRESH_BASE_MS = 60000;

function useEngine(speedMultiplier: number, paused: boolean) {
  const [cycle, setCycle] = useState(0);
  const [progress, setProgress] = useState(0);
  const [activeLayer, setActiveLayer] = useState(-1);
  const [lastCycleAt, setLastCycleAt] = useState(Date.now());
  const [snapshot, setSnapshot] = useState<SimSnapshot | null>(null);
  const [flashedSymbols, setFlashedSymbols] = useState<Map<string, string>>(new Map());
  const setWsConnected = useMarketStore((s) => s.setWsConnected);
  const setContext = useMarketStore((s) => s.setContext);
  const setRankings = useMarketStore((s) => s.setRankings);
  const storeLongRankings = useMarketStore((s) => s.longRankings);
  const storeContext = useMarketStore((s) => s.context);

  useEffect(() => {
    const universe = genUniverse(0);
    const ctx = genMarketContext(0);
    const pipeline = genPipelineStatus(0, Date.now());
    setSnapshot({ universe, ctx, pipeline });
    // Populate Zustand store so components reading from store get data
    syncToStore(universe, ctx);
  }, []);

  // Sync simulated data to Zustand store when WebSocket hasn't delivered real data
  function syncToStore(universe: { longs: SimStock[]; shorts: SimStock[] }, ctx: SimMarketContext) {
    if (!storeContext) setContext(ctx as any);
    if (storeLongRankings.length === 0) {
      setRankings(
        universe.longs.map(s => ({ symbol: s.symbol, instrument_key: s.instrument_key, direction: 'LONG' as const, score: s.score, setup_type: s.setup_type, confluence_score: s.confluence_score, net_rr: s.net_rr, actionability_tier: (s.tier as any) || 'Research-Only', rank_movement: s.rank_movement, liquidity_quality: (s.liquidity_quality as any) || 'Good', price: s.price, change_pct: s.change_pct, sector_name: s.sector_name, sparkline: s.spark, state: s.state, edge_tier: s.edge_tier })),
        universe.shorts.map(s => ({ symbol: s.symbol, instrument_key: s.instrument_key, direction: 'SHORT' as const, score: s.score, setup_type: s.setup_type, confluence_score: s.confluence_score, net_rr: s.net_rr, actionability_tier: (s.tier as any) || 'Research-Only', rank_movement: s.rank_movement, liquidity_quality: (s.liquidity_quality as any) || 'Good', price: s.price, change_pct: s.change_pct, sector_name: s.sector_name, sparkline: s.spark, state: s.state, edge_tier: s.edge_tier })),
      );
    }
  }

  useEffect(() => {
    if (paused) return;
    const period = REFRESH_BASE_MS / speedMultiplier;
    const tickInterval = 200;
    let elapsed = 0;

    const tick = setInterval(() => {
      elapsed += tickInterval;
      const p = elapsed / period;
      if (p >= 1) {
        const newCycle = cycle + 1;
        elapsed = 0;
        setProgress(0);
        runCycle(newCycle);
      } else {
        setProgress(p);
        if (p > 0.75) {
          setActiveLayer(Math.min(9, Math.floor(((p - 0.75) / 0.25) * 10)));
        } else {
          setActiveLayer(-1);
        }
      }
    }, tickInterval);

    function runCycle(c: number) {
      const prevSnapshot = snapshot;
      const universe = genUniverse(c);
      const ctx = genMarketContext(c);
      const ts = Date.now();
      const pipeline = genPipelineStatus(c, ts);

      const flashes = new Map<string, string>();
      if (prevSnapshot) {
        const allPrev = [...prevSnapshot.universe.longs, ...prevSnapshot.universe.shorts];
        const prevByS = new Map(allPrev.map((s) => [s.symbol, s]));
        for (const s of [...universe.longs, ...universe.shorts]) {
          const p = prevByS.get(s.symbol);
          if (!p) flashes.set(s.symbol, 'animate-flash-row');
          else if (s.score_change > 2) flashes.set(s.symbol, 'animate-flash-up');
          else if (s.score_change < -2) flashes.set(s.symbol, 'animate-flash-down');
        }
      }

      setSnapshot({ universe, ctx, pipeline });
      setLastCycleAt(ts);
      setCycle(c);
      setActiveLayer(-1);
      setWsConnected(true);
      setFlashedSymbols(flashes);
      syncToStore(universe, ctx);
      setTimeout(() => setFlashedSymbols(new Map()), 1500);
    }

    return () => { clearInterval(tick); };
  }, [cycle, paused, speedMultiplier]);

  return { cycle, progress, activeLayer, lastCycleAt, snapshot, flashedSymbols };
}

export default function App() {
  useWebSocket();

  const [speed] = useState(6);
  const [paused, setPaused] = useState(false);
  const [selected, setSelected] = useState<SimStock | null>(null);
  const [viewMode, setViewMode] = useState<'journey' | 'cards'>('journey');
  const [learnMode, setLearnMode] = useState(false);
  const [inspectedLayer, setInspectedLayer] = useState<string | null>(null);
  const [viewport, setViewport] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 1200,
    mobile: typeof window !== 'undefined' ? window.innerWidth < 768 : false,
  });

  const { cycle, progress, activeLayer, lastCycleAt, snapshot, flashedSymbols } =
    useEngine(speed, paused);

  const realContext = useMarketStore((s) => s.context);

  useEffect(() => {
    if (!selected && snapshot && snapshot.universe.longs.length > 0) {
      setSelected(snapshot.universe.longs[0]);
    }
  }, [snapshot, selected]);

  useEffect(() => {
    const onResize = () => {
      const w = window.innerWidth;
      setViewport({ width: w, mobile: w < 768 });
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const funnel = useMemo(() => {
    if (!snapshot) return {};
    return computeFunnel(snapshot);
  }, [snapshot]);

  // Cycle activity events from simulator
  const activityEvents = useCycleActivity(snapshot ?? {
    universe: { longs: [], shorts: [], cycle: 0 },
    ctx: genMarketContext(0),
    pipeline: [],
  }, cycle);

  // Alert feed from simulator (runs independently, AlertToast reads from Zustand)
  useAlertFeed(snapshot ?? {
    universe: { longs: [], shorts: [], cycle: 0 },
    ctx: genMarketContext(0),
    pipeline: [],
  }, cycle);

  const ctx = (snapshot?.ctx as SimMarketContext | undefined) ?? realContext;

  const onCloseLayer = useCallback(() => setInspectedLayer(null), []);
  const onSwitchLayer = useCallback((k: string) => setInspectedLayer(k), []);

  const handleSelectSymbol = useCallback(
    (sym: string) => {
      if (!snapshot) return;
      const all = [...snapshot.universe.longs, ...snapshot.universe.shorts];
      const found = all.find((s) => s.symbol === sym);
      if (found) setSelected(found);
    },
    [snapshot],
  );

  const isMobile = viewport.mobile;

  return (
    <div className="flex h-[100dvh] flex-col bg-[var(--bg-base)] text-[var(--text-primary)]">
      <Header
        progress={progress} paused={paused} cycle={cycle}
        onPauseToggle={() => setPaused(!paused)}
        learnMode={learnMode}
        onLearnToggle={(v: boolean) => setLearnMode(v)}
      />

      {snapshot ? (
        <FunnelStrip
          layers={snapshot.pipeline}
          activeLayer={activeLayer}
          funnel={funnel}
          onInspect={(k: string) => setInspectedLayer((prev) => (prev === k ? null : k))}
          inspectKey={inspectedLayer}
          learnMode={learnMode}
        />
      ) : (
        <PipelineStatusBar activeLayer={activeLayer} />
      )}

      <RegimeBanner />

      {isMobile ? (
        <MobileLayout
          snapshot={snapshot} selected={selected} setSelected={setSelected}
          viewMode={viewMode} setViewMode={setViewMode}
          learnMode={learnMode} activeLayer={activeLayer}
          inspectedLayer={inspectedLayer}
          onCloseLayer={onCloseLayer} onSwitchLayer={onSwitchLayer}
          ctx={ctx}
          flashedSymbols={flashedSymbols}
          activityEvents={activityEvents}
          handleSelectSymbol={handleSelectSymbol}
        />
      ) : (
        <div className="flex flex-1 overflow-hidden p-2.5" style={{ gap: 10 }}>
          <div className="flex w-[360px] shrink-0 flex-col gap-2">
            <RankingsPanel
              onSelectSymbol={handleSelectSymbol}
              entries={snapshot ? [...snapshot.universe.longs, ...snapshot.universe.shorts] : undefined}
              flashedSymbols={flashedSymbols}
            />
          </div>

          <DetailColumn
            selected={selected} ctx={ctx} snapshot={snapshot}
            viewMode={viewMode} setViewMode={setViewMode}
            learnMode={learnMode} activeLayer={activeLayer}
            inspectedLayer={inspectedLayer}
            onCloseLayer={onCloseLayer} onSwitchLayer={onSwitchLayer}
            setSelected={setSelected}
          />

          <div className="flex w-[280px] shrink-0 flex-col gap-2">
            <CycleActivity
              events={activityEvents}
              onSelect={handleSelectSymbol}
              selectedSymbol={selected?.symbol ?? null}
            />
            <ActiveMonitor />
            <EdgePanel />
          </div>
        </div>
      )}

      <HealthStrip
        pipeline={snapshot?.pipeline ?? []}
        cycle={cycle}
        paused={paused}
        lastCycleAt={lastCycleAt}
      />
      <AlertToast />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// DetailColumn
function DetailColumn({
  selected, ctx, snapshot, viewMode, setViewMode, learnMode, activeLayer,
  inspectedLayer, onCloseLayer, onSwitchLayer, setSelected,
}: {
  selected: SimStock | null;
  ctx: any;
  snapshot: SimSnapshot | null;
  viewMode: string;
  setViewMode: (v: 'journey' | 'cards') => void;
  learnMode: boolean;
  activeLayer: number;
  inspectedLayer: string | null;
  onCloseLayer: () => void;
  onSwitchLayer: (k: string) => void;
  setSelected: (s: SimStock | null) => void;
}) {
  return (
    <div className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
      {!inspectedLayer && (
        <div className="flex items-center gap-2 border-b border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] px-3 py-1.5">
          <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-tertiary)]">
            Inspector
          </span>
          {selected && (
            <span className="text-[11px] font-bold text-[var(--text-primary)]">
              {selected.symbol}
            </span>
          )}
          <span className="flex-1" />
          <span className="hidden text-[9px] text-[var(--text-tertiary)] sm:inline">
            click any L<i>n</i> tile above
          </span>
          <div className="inline-flex gap-0.5 rounded bg-[var(--bg-base)] p-0.5">
            {([
              { v: 'journey' as const, label: 'Journey' },
              { v: 'cards' as const, label: 'Cards' },
            ]).map((opt) => (
              <button
                key={opt.v}
                onClick={() => setViewMode(opt.v)}
                className="touch-target rounded px-3 py-1.5 text-[10px] font-bold tracking-wide transition-colors"
                style={{
                  color: viewMode === opt.v ? 'var(--accent)' : 'var(--text-tertiary)',
                  background: viewMode === opt.v ? 'var(--accent-dim)' : 'transparent',
                }}
              >
                {opt.label.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      )}
      <div className="flex flex-1 flex-col overflow-hidden">
        {inspectedLayer && snapshot ? (
          <LayerInspector
            layerKey={inspectedLayer}
            snapshot={snapshot}
            ctx={ctx}
            onClose={onCloseLayer}
            onSwitchLayer={onSwitchLayer}
            onSelectStock={(stock: SimStock) => {
              setSelected(stock);
              onCloseLayer();
            }}
          />
        ) : viewMode === 'cards' ? (
          <DetailPanel
            symbol={selected?.symbol ?? ''}
            stock={selected}
            ctx={ctx}
          />
        ) : selected ? (
          <LayerJourney
            entry={selected}
            ctx={ctx}
            learnMode={learnMode}
            activeLayer={activeLayer}
          />
        ) : (
          <DetailPanel symbol="" />
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Mobile Layout — 4 tabs
function MobileLayout({
  snapshot, selected, setSelected,
  viewMode, setViewMode, learnMode, activeLayer,
  inspectedLayer, onCloseLayer, onSwitchLayer, ctx,
  flashedSymbols, activityEvents, handleSelectSymbol,
}: {
  snapshot: SimSnapshot | null;
  selected: SimStock | null;
  setSelected: (s: SimStock | null) => void;
  viewMode: string;
  setViewMode: (v: 'journey' | 'cards') => void;
  learnMode: boolean;
  activeLayer: number;
  inspectedLayer: string | null;
  onCloseLayer: () => void;
  onSwitchLayer: (k: string) => void;
  ctx: any;
  flashedSymbols: Map<string, string>;
  activityEvents: any[];
  handleSelectSymbol: (sym: string) => void;
}) {
  const [tab, setTab] = useState<'rankings' | 'detail' | 'theses' | 'activity'>('rankings');

  useEffect(() => {
    if (inspectedLayer) setTab('detail');
  }, [inspectedLayer]);

  const onSelect = (sym: string) => {
    handleSelectSymbol(sym);
    setTab('detail');
  };

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]">
        {[
          ['rankings', 'Top 25'],
          ['detail', 'Detail'],
          ['theses', 'Theses'],
          ['activity', 'Activity'],
        ].map(([k, lbl]) => (
          <button
            key={k}
            onClick={() => setTab(k as typeof tab)}
            className="touch-target flex-1 py-3 text-[12px] font-semibold transition-colors"
            style={{
              color: tab === k ? 'var(--text-primary)' : 'var(--text-tertiary)',
              borderBottom: `2px solid ${tab === k ? 'var(--accent)' : 'transparent'}`,
              background: tab === k ? 'var(--bg-surface-raised)' : 'transparent',
            }}
          >
            {lbl}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {tab === 'rankings' && (
          <div className="flex flex-col gap-2">
            <RankingsPanel
              onSelectSymbol={onSelect}
              entries={snapshot ? [...snapshot.universe.longs, ...snapshot.universe.shorts] : undefined}
              flashedSymbols={flashedSymbols}
            />
          </div>
        )}
        {tab === 'detail' && (
          <DetailColumn
            selected={selected} ctx={ctx} snapshot={snapshot}
            viewMode={viewMode} setViewMode={setViewMode}
            learnMode={learnMode} activeLayer={activeLayer}
            inspectedLayer={inspectedLayer}
            onCloseLayer={onCloseLayer} onSwitchLayer={onSwitchLayer}
            setSelected={setSelected}
          />
        )}
        {tab === 'theses' && (
          <div className="flex flex-col gap-2">
            <ActiveMonitor />
            <EdgePanel />
          </div>
        )}
        {tab === 'activity' && (
          <CycleActivity
            events={activityEvents}
            onSelect={onSelect}
            selectedSymbol={selected?.symbol ?? null}
          />
        )}
      </div>
    </div>
  );
}
