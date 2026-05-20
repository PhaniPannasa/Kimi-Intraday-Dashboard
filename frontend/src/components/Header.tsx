'use client';

import { useState, useEffect } from 'react';
import { useTelemetry } from '@/hooks/useTelemetry';

interface HeaderProps {
  progress: number;
  paused: boolean;
  cycle: number;
  onPauseToggle: () => void;
  learnMode?: boolean;
  onLearnToggle?: (v: boolean) => void;
}

/** Derive the connection-status label from market phase + paused flag.
 *  LIVE only when pipeline phase is "live" AND not paused. */
function statusLabel(phase: string | undefined, paused: boolean): { label: string; isLive: boolean } {
  if (paused) return { label: 'PAUSED', isLive: false };
  switch (phase) {
    case 'live':       return { label: 'LIVE', isLive: true };
    case 'pre-market': return { label: 'PRE-MARKET', isLive: false };
    case 'closing':    return { label: 'CLOSING', isLive: false };
    case 'closed':     return { label: 'CLOSED', isLive: false };
    default:           return { label: 'OFFLINE', isLive: false };
  }
}

function ClockIST() {
  const [time, setTime] = useState(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const utc = time.getTime() + (time.getTimezoneOffset() * 60000);
  const istOffset = 5.5 * 60 * 60000;
  const ist = new Date(utc + istOffset);
  const hh = String(ist.getHours()).padStart(2, '0');
  const mm = String(ist.getMinutes()).padStart(2, '0');
  const ss = String(ist.getSeconds()).padStart(2, '0');

  return (
    <span className="font-mono text-[var(--text-secondary)] text-sm">
      {hh}:{mm}<span className="hidden text-[var(--text-tertiary)] sm:inline">:{ss}</span>
      <span className="hidden sm:inline"> IST</span>
    </span>
  );
}

function ConnectionDot({ label, isLive }: { label: string; isLive: boolean }) {
  const color = isLive ? 'var(--trade-long)' : 'var(--trade-neutral)';
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className="animate-pulse-dot inline-block h-1.5 w-1.5 rounded-full"
        style={{ background: color }}
      />
      <span
        className="text-xs font-semibold tracking-wide"
        style={{ color }}
      >
        {label}
      </span>
    </span>
  );
}

function RefreshRing({ progress, paused, cycle }: { progress: number; paused: boolean; cycle: number }) {
  const r = 11;
  const c = 2 * Math.PI * r;
  const dash = c * (1 - progress);

  return (
    <div className="inline-flex items-center gap-2">
      <div className="relative h-7 w-7">
        <svg
          width="28"
          height="28"
          viewBox="0 0 28 28"
          className="-rotate-90"
        >
          <circle
            cx="14"
            cy="14"
            r={r}
            stroke="var(--border-subtle)"
            strokeWidth="2"
            fill="none"
          />
          <circle
            cx="14"
            cy="14"
            r={r}
            stroke="var(--accent)"
            strokeWidth="2"
            fill="none"
            strokeDasharray={c}
            strokeDashoffset={dash}
            className="transition-[stroke-dashoffset] duration-200"
            style={{ transition: 'stroke-dashoffset 200ms linear' }}
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center font-mono text-[9px] text-[var(--text-secondary)]">
          {paused ? '||' : Math.ceil((1 - progress) * 60)}
        </span>
      </div>
      <div className="hidden flex-col text-[10px] leading-tight sm:flex">
        <span className="text-[var(--text-tertiary)] uppercase tracking-wide">Next cycle</span>
        <span className="font-mono text-[var(--text-secondary)]">#{String(cycle).padStart(5, '0')}</span>
      </div>
    </div>
  );
}

export function Header({ progress, paused, cycle, onPauseToggle, learnMode, onLearnToggle }: HeaderProps) {
  const { data: telemetry } = useTelemetry();
  const phase = telemetry?.pipeline?.phase;
  return (
    <header
      className="flex items-center gap-2 border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2 py-1.5 sm:gap-3 sm:px-4 sm:py-2"
    >
      {/* Logo + Title */}
      <div className="flex items-center gap-2">
        <div
          className="flex h-5 w-5 items-center justify-center rounded text-xs font-extrabold text-[var(--bg-base)]"
          style={{
            background: 'linear-gradient(135deg, var(--trade-long) 0%, var(--accent) 100%)',
          }}
        >
          K
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-sm font-bold tracking-tight sm:text-base">Kimi Intraday</span>
          <span className="hidden text-[10px] text-[var(--text-tertiary)] sm:block">
            NSE Nifty 100 · Research Only
          </span>
        </div>
      </div>

      <div className="hidden h-4 w-px bg-[var(--border-subtle)] sm:block" />

      {/* Phase badges */}
      <div className="hidden items-center gap-1.5 lg:flex">
        <span className="rounded bg-[var(--accent-dim)] px-1.5 py-0.5 text-[10px] font-semibold text-[var(--accent)]">
          PHASE 1
        </span>
        <span className="rounded bg-[var(--bg-surface-raised)] px-1.5 py-0.5 text-[10px] font-semibold text-[var(--text-tertiary)]">
          NO LIVE ORDERS
        </span>
      </div>

      <div className="flex-1" />

      {/* Learn mode toggle */}
      {onLearnToggle && (
        <>
          <button
            onClick={() => onLearnToggle(!learnMode)}
            title={learnMode ? 'Hide learn captions' : 'Show learn captions'}
            className="inline-flex h-6 items-center gap-1 rounded border px-2 text-[10px] font-bold tracking-wide transition-colors"
            style={{
              borderColor: learnMode ? 'var(--accent-soft)' : 'var(--border-subtle)',
              background: learnMode ? 'var(--accent-dim)' : 'var(--bg-surface-raised)',
              color: learnMode ? 'var(--accent)' : 'var(--text-secondary)',
            }}
          >
            <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
              <path d="M1 2.5h4.5v7l-.6-.4-.6-.3-.6-.2-.6-.1H1zM10 2.5H5.5v7l.6-.4.6-.3.6-.2.6-.1H10z" stroke="currentColor" strokeWidth="0.9" strokeLinejoin="round" />
            </svg>
            LEARN
          </button>
          <div className="h-4 w-px bg-[var(--border-subtle)]" />
        </>
      )}

      {/* Clock */}
      <ClockIST />

      <div className="h-4 w-px bg-[var(--border-subtle)]" />

      {/* Refresh ring */}
      <RefreshRing progress={progress} paused={paused} cycle={cycle} />

      {/* Pause button */}
      <button
        onClick={onPauseToggle}
        aria-label={paused ? 'Resume engine' : 'Pause engine'}
        aria-pressed={paused}
        title={paused ? 'Resume' : 'Pause'}
        className="flex h-6 w-6 items-center justify-center rounded border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] text-[var(--text-secondary)] hover:border-[var(--border-strong)]"
      >
        {paused ? (
          <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
            <path d="M2 1l7 4-7 4z" fill="currentColor" />
          </svg>
        ) : (
          <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
            <rect x="2" y="1" width="2.5" height="8" fill="currentColor" />
            <rect x="5.5" y="1" width="2.5" height="8" fill="currentColor" />
          </svg>
        )}
      </button>

      <div className="h-4 w-px bg-[var(--border-subtle)]" />

      {/* WS connection — gated on real pipeline phase */}
      <ConnectionDot {...statusLabel(phase, paused)} />
    </header>
  );
}