'use client';

import { useState, useEffect } from 'react';

interface HeaderProps {
  progress: number;
  paused: boolean;
  cycle: number;
  onPauseToggle: () => void;
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
      {hh}:{mm}<span className="text-[var(--text-tertiary)]">:{ss}</span> IST
    </span>
  );
}

function ConnectionDot({ connected }: { connected: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className="animate-pulse-dot inline-block h-1.5 w-1.5 rounded-full"
        style={{
          background: connected ? 'var(--trade-long)' : 'var(--trade-short)',
        }}
      />
      <span
        className="text-xs font-semibold tracking-wide"
        style={{
          color: connected ? 'var(--trade-long)' : 'var(--trade-short)',
        }}
      >
        {connected ? 'LIVE' : 'OFFLINE'}
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
      <div className="flex flex-col text-[10px] leading-tight">
        <span className="text-[var(--text-tertiary)] uppercase tracking-wide">Next cycle</span>
        <span className="font-mono text-[var(--text-secondary)]">#{String(cycle).padStart(5, '0')}</span>
      </div>
    </div>
  );
}

export function Header({ progress, paused, cycle, onPauseToggle }: HeaderProps) {
  return (
    <header
      className="flex items-center gap-3 border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 md:px-4"
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
          <span className="text-base font-bold tracking-tight">Kimi Intraday</span>
          <span className="hidden text-[10px] text-[var(--text-tertiary)] sm:block">
            NSE Nifty 100 · Research Only
          </span>
        </div>
      </div>

      <div className="h-4 w-px bg-[var(--border-subtle)]" />

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

      {/* WS connection */}
      <ConnectionDot connected={!paused} />
    </header>
  );
}