'use client';

import { useState, useEffect, useCallback } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useMarketStore } from '@/stores/marketStore';
import { useMarketContext } from '@/hooks/useMarketContext';
import { useRankings } from '@/hooks/useRankings';
import { useFunnelCounts } from '@/hooks/useFunnelCounts';
import { useActiveTheses } from '@/hooks/useActiveTheses';
import { useEdgeTiers } from '@/hooks/useEdgeTiers';
import { useActivityEvents } from '@/hooks/useActivityEvents';
import { usePipelineStatus } from '@/hooks/usePipelineStatus';
import { Header } from '@/components/Header';
import { PipelineStatusBar } from '@/components/PipelineStatusBar';
import { FunnelStrip } from '@/components/FunnelStrip';
import { RegimeBanner } from '@/components/RegimeBanner';
import { RankingsPanel } from '@/components/RankingsPanel';
import { DetailPanel } from '@/components/DetailPanel';
import { LayerJourney } from '@/components/LayerJourney';
import { LayerInspector } from '@/components/LayerInspector';
import { CycleActivity } from '@/components/CycleActivity';
import { ActiveMonitor } from '@/components/ActiveMonitor';
import { EdgePanel } from '@/components/EdgePanel';
import { AlertToast } from '@/components/AlertToast';
import { HealthStrip } from '@/components/HealthStrip';
import { DataSourceDebugPanel } from '@/components/DataSourceDebugPanel';
import type { RankingEntry } from '@/types/api';

export default function App() {
  useWebSocket();
  useMarketContext();
  useRankings('long');
  useRankings('short');
  const { data: pipelineStatus } = usePipelineStatus();
  const { data: funnel } = useFunnelCounts();
  useActiveTheses();
  useEdgeTiers();
  const { data: activityEvents } = useActivityEvents();

  const longRankings = useMarketStore((s) => s.longRankings);
  const shortRankings = useMarketStore((s) => s.shortRankings);
  const storedContext = useMarketStore((s) => s.context);
  const ctx = storedContext ?? {
    regime: 'Range-Bound',
    regime_confidence: 0,
    volatility_qualifier: 'Normal',
    vix_band: 'Normal',
    vix_trajectory: 'Stable',
    vix_value: 0,
    time_bucket: 'Unknown',
    event_flag: null,
    breadth: 'Mixed',
    premarket_bias: 'Neutral',
    bank_nifty_divergence: 0,
  };

  const [selected, setSelected] = useState<RankingEntry | null>(null);
  const [viewMode, setViewMode] = useState<'journey' | 'cards'>('journey');
  const [learnMode, setLearnMode] = useState(false);
  const [inspectedLayer, setInspectedLayer] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);
  const [viewport, setViewport] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 1200,
    mobile: typeof window !== 'undefined' ? window.innerWidth < 768 : false,
  });

  useEffect(() => {
    if (!selected && longRankings.length > 0) {
      setSelected(longRankings[0]);
    }
  }, [longRankings, selected]);

  useEffect(() => {
    const onResize = () => {
      const w = window.innerWidth;
      setViewport({ width: w, mobile: w < 768 });
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const handleSelectSymbol = useCallback(
    (sym: string) => {
      const found = [...longRankings, ...shortRankings].find((s) => s.symbol === sym);
      if (found) setSelected(found);
    },
    [longRankings, shortRankings],
  );

  const onCloseLayer = useCallback(() => setInspectedLayer(null), []);
  const onSwitchLayer = useCallback((k: string) => setInspectedLayer(k), []);

  const isMobile = viewport.mobile;
  const cycle = pipelineStatus?.cycle_number ?? 0;
  const layers: import('@/types/api').PipelineLayerStatus[] = pipelineStatus
    ? Object.values(pipelineStatus.layers)
    : [];

  return (
    <div className="flex h-[100dvh] flex-col bg-[var(--bg-base)] text-[var(--text-primary)]">
      <Header
        progress={0}
        paused={paused}
        cycle={cycle}
        onPauseToggle={() => setPaused(!paused)}
        learnMode={learnMode}
        onLearnToggle={(v: boolean) => setLearnMode(v)}
      />

      {pipelineStatus ? (
        <FunnelStrip
          layers={layers}
          activeLayer={-1}
          funnel={funnel ?? {}}
          onInspect={(k: string) => setInspectedLayer((prev) => (prev === k ? null : k))}
          inspectKey={inspectedLayer}
          learnMode={learnMode}
        />
      ) : (
        <PipelineStatusBar activeLayer={-1} />
      )}

      <RegimeBanner />

      {isMobile ? (
        <MobileLayout
          longRankings={longRankings}
          shortRankings={shortRankings}
          selected={selected}
          setSelected={setSelected}
          viewMode={viewMode}
          setViewMode={setViewMode}
          learnMode={learnMode}
          inspectedLayer={inspectedLayer}
          onCloseLayer={onCloseLayer}
          onSwitchLayer={onSwitchLayer}
          activityEvents={activityEvents?.events ?? []}
          handleSelectSymbol={handleSelectSymbol}
          ctx={ctx}
        />
      ) : (
        <div className="flex flex-1 overflow-hidden p-2.5" style={{ gap: 10 }}>
          <div className="flex w-[360px] shrink-0 flex-col gap-2">
            <RankingsPanel
              onSelectSymbol={handleSelectSymbol}
              entries={[...longRankings, ...shortRankings]}
              flashedSymbols={new Map()}
            />
          </div>

          <DetailColumn
            selected={selected}
            longRankings={longRankings}
            shortRankings={shortRankings}
            viewMode={viewMode}
            setViewMode={setViewMode}
            learnMode={learnMode}
            inspectedLayer={inspectedLayer}
            onCloseLayer={onCloseLayer}
            onSwitchLayer={onSwitchLayer}
            setSelected={setSelected}
            ctx={ctx}
          />

          <div className="flex w-[280px] shrink-0 flex-col gap-2">
            <CycleActivity
              events={activityEvents?.events ?? []}
              onSelect={handleSelectSymbol}
              selectedSymbol={selected?.symbol ?? null}
            />
            <ActiveMonitor />
            <EdgePanel />
          </div>
        </div>
      )}

      <HealthStrip
        pipeline={layers}
        cycle={cycle}
        paused={paused}
        lastCycleAt={pipelineStatus?.last_cycle_at ? Date.parse(pipelineStatus.last_cycle_at) : 0}
      />
      <AlertToast />
      <DataSourceDebugPanel />
    </div>
  );
}

function DetailColumn({
  selected, longRankings, shortRankings, viewMode, setViewMode, learnMode,
  inspectedLayer, onCloseLayer, onSwitchLayer, setSelected, ctx,
}: {
  selected: RankingEntry | null;
  longRankings: RankingEntry[];
  shortRankings: RankingEntry[];
  viewMode: string;
  setViewMode: (v: 'journey' | 'cards') => void;
  learnMode: boolean;
  inspectedLayer: string | null;
  onCloseLayer: () => void;
  onSwitchLayer: (k: string) => void;
  setSelected: (s: RankingEntry | null) => void;
  ctx: any;
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
        {inspectedLayer ? (
          <LayerInspector
            layerKey={inspectedLayer}
            stocks={[...longRankings, ...shortRankings] as any}
            ctx={ctx}
            onClose={onCloseLayer}
            onSwitchLayer={onSwitchLayer}
            onSelectStock={(stock: any) => {
              setSelected(stock);
              onCloseLayer();
            }}
          />
        ) : viewMode === 'cards' ? (
          <DetailPanel symbol={selected?.symbol ?? ''} stock={selected as any} ctx={ctx} />
        ) : selected ? (
          <LayerJourney entry={selected as any} ctx={ctx} learnMode={learnMode} activeLayer={-1} />
        ) : (
          <DetailPanel symbol="" />
        )}
      </div>
    </div>
  );
}

function MobileLayout({
  longRankings, shortRankings, selected, setSelected,
  viewMode, setViewMode, learnMode,
  inspectedLayer, onCloseLayer, onSwitchLayer,
  activityEvents, handleSelectSymbol, ctx,
}: {
  longRankings: RankingEntry[];
  shortRankings: RankingEntry[];
  selected: RankingEntry | null;
  setSelected: (s: RankingEntry | null) => void;
  viewMode: string;
  setViewMode: (v: 'journey' | 'cards') => void;
  learnMode: boolean;
  inspectedLayer: string | null;
  onCloseLayer: () => void;
  onSwitchLayer: (k: string) => void;
  activityEvents: any[];
  handleSelectSymbol: (sym: string) => void;
  ctx: any;
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
          <RankingsPanel
            onSelectSymbol={onSelect}
            entries={[...longRankings, ...shortRankings]}
            flashedSymbols={new Map()}
          />
        )}
        {tab === 'detail' && (
          <DetailColumn
            selected={selected}
            longRankings={longRankings}
            shortRankings={shortRankings}
            viewMode={viewMode}
            setViewMode={setViewMode}
            learnMode={learnMode}
            inspectedLayer={inspectedLayer}
            onCloseLayer={onCloseLayer}
            onSwitchLayer={onSwitchLayer}
            setSelected={setSelected}
            ctx={ctx}
          />
        )}
        {tab === 'theses' && (
          <>
            <ActiveMonitor />
            <EdgePanel />
          </>
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
