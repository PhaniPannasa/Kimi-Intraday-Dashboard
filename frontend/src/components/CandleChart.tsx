import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/lib/apiFetch';
import type { CandleResponse } from '@/types/api';

interface CandleChartProps {
  symbol: string;
  trigger?: number;
  invalidation?: number;
  t1?: number;
  t2?: number;
  vwap?: number;
  width?: number;
  height?: number;
}

export function CandleChart({
  symbol,
  trigger,
  invalidation,
  t1,
  t2,
  vwap,
  width = 480,
  height = 200,
}: CandleChartProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['candles', symbol],
    queryFn: async () => {
      const result = await apiFetch<CandleResponse>(
        `/api/market/candles/${encodeURIComponent(symbol)}?limit=60`
      );
      return result.data;
    },
    staleTime: 60000,
    enabled: !!symbol,
  });

  if (isLoading) {
    return (
      <div className="flex h-[200px] items-center justify-center rounded border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]">
        <div className="h-4 w-1/3 animate-pulse rounded bg-[var(--bg-surface-raised)]" />
      </div>
    );
  }

  const candles = data?.candles;
  if (!candles || candles.length === 0) {
    return (
      <div className="flex h-[200px] items-center justify-center rounded border border-dashed border-[var(--border-subtle)] bg-[var(--bg-surface)] text-xs text-[var(--text-tertiary)]">
        No candle data for {symbol}
      </div>
    );
  }

  // Compute Y range from all OHLC values + overlay levels
  const overlayLevels = [trigger, invalidation, t1, t2, vwap].filter(
    (v): v is number => v != null && v > 0
  );
  const allPrices = candles.flatMap((c) => [c.h, c.l, ...overlayLevels]);
  const yMin = Math.min(...allPrices);
  const yMax = Math.max(...allPrices);
  const yPad = (yMax - yMin) * 0.05 || 1;
  const yRange = { min: yMin - yPad, max: yMax + yPad };

  const padLeft = 8;
  const padRight = 56;
  const padTop = 8;
  const padBottom = 18;
  const innerW = width - padLeft - padRight;
  const innerH = height - padTop - padBottom;
  const candleW = Math.max(1, (innerW / candles.length) * 0.75);

  const scaleY = (v: number) =>
    padTop + innerH * (1 - (v - yRange.min) / (yRange.max - yRange.min));
  const scaleX = (i: number) =>
    padLeft + (innerW / candles.length) * (i + 0.5);

  const lastCandle = candles[candles.length - 1];
  const isMobile = width < 400;

  return (
    <div className="flex flex-col gap-1">
      {/* Header */}
      <div className="flex items-center gap-2 px-1 text-[10px] uppercase tracking-wider text-[var(--text-tertiary)]">
        <span>1-min Candles · last hour</span>
        <span className="flex-1" />
        <span className="font-mono tabular-nums text-[var(--text-primary)]">
          O {lastCandle.o.toFixed(1)}
        </span>
        <span className="font-mono tabular-nums text-[var(--trade-long)]">
          H {lastCandle.h.toFixed(1)}
        </span>
        <span className="font-mono tabular-nums text-[var(--trade-short)]">
          L {lastCandle.l.toFixed(1)}
        </span>
        <span className="font-mono tabular-nums text-[var(--text-primary)]">
          C {lastCandle.c.toFixed(1)}
        </span>
      </div>

      {/* SVG Chart */}
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        height={isMobile ? 160 : height}
        preserveAspectRatio="xMidYMid meet"
        className="rounded border border-[var(--border-subtle)]"
        style={{ background: 'var(--bg-surface-raised)' }}
      >
        {/* Gridlines */}
        {[0.25, 0.5, 0.75].map((pct) => (
          <line
            key={pct}
            x1={padLeft}
            x2={width - padRight}
            y1={padTop + innerH * (1 - pct)}
            y2={padTop + innerH * (1 - pct)}
            stroke="var(--border-subtle)"
            strokeWidth={0.5}
            strokeDasharray="2 3"
          />
        ))}

        {/* Reward zone (trigger → T2) */}
        {trigger != null && t2 != null && (
          <rect
            x={padLeft}
            y={Math.min(scaleY(trigger), scaleY(t2))}
            width={innerW}
            height={Math.abs(scaleY(t2) - scaleY(trigger))}
            fill="var(--trade-long)"
            opacity={0.04}
          />
        )}

        {/* Risk zone (invalidation → trigger) */}
        {invalidation != null && trigger != null && (
          <rect
            x={padLeft}
            y={Math.min(scaleY(trigger), scaleY(invalidation))}
            width={innerW}
            height={Math.abs(scaleY(invalidation) - scaleY(trigger))}
            fill="var(--trade-short)"
            opacity={0.04}
          />
        )}

        {/* Candles */}
        {candles.map((c, i) => {
          const bullish = c.c >= c.o;
          const color = bullish
            ? 'var(--trade-long)'
            : 'var(--trade-short)';
          const x = scaleX(i) - candleW / 2;
          const bodyH = Math.max(1, Math.abs(scaleY(c.c) - scaleY(c.o)));
          const bodyY = bullish ? scaleY(c.c) : scaleY(c.o);

          return (
            <g key={i}>
              {/* Wick */}
              <line
                x1={scaleX(i)}
                x2={scaleX(i)}
                y1={scaleY(c.h)}
                y2={scaleY(c.l)}
                stroke={color}
                strokeWidth={0.8}
              />
              {/* Body */}
              <rect
                x={x}
                y={bodyY}
                width={candleW}
                height={bodyH}
                fill={color}
              />
            </g>
          );
        })}

        {/* Overlay lines */}
        {[
          { value: vwap, color: 'var(--trade-neutral)', dash: '3 2', label: 'VWAP' },
          { value: t2, color: 'var(--trade-long)', dash: '', label: 'T2' },
          { value: t1, color: 'var(--trade-long)', dash: '4 3', label: 'T1' },
          { value: trigger, color: 'var(--accent)', dash: '', label: 'TRIG' },
          { value: invalidation, color: 'var(--trade-short)', dash: '', label: 'SL' },
        ].map(
          (overlay) =>
            overlay.value != null &&
            overlay.value > yRange.min &&
            overlay.value < yRange.max && (
              <g key={overlay.label}>
                <line
                  x1={padLeft}
                  x2={width - padRight}
                  y1={scaleY(overlay.value)}
                  y2={scaleY(overlay.value)}
                  stroke={overlay.color}
                  strokeWidth={overlay.label === 'TRIG' || overlay.label === 'SL' ? 1.4 : 1}
                  strokeDasharray={overlay.dash || undefined}
                />
                <text
                  x={width - padRight + 4}
                  y={scaleY(overlay.value) + 3}
                  fill={overlay.color}
                  fontSize={9}
                  fontFamily="var(--font-mono), monospace"
                  fontWeight={overlay.label === 'TRIG' || overlay.label === 'SL' ? 700 : 600}
                >
                  {overlay.label}{' '}
                  {overlay.value.toFixed(overlay.value > 1000 ? 0 : 2)}
                </text>
              </g>
            )
        )}

        {/* X-axis time labels */}
        {candles.map((_c, i) => {
          // Label every ~6 candles
          if (i % 6 !== 0 && i !== candles.length - 1) return null;
          return (
            <text
              key={`t-${i}`}
              x={scaleX(i)}
              y={height - 3}
              fill="var(--text-tertiary)"
              fontSize={8.5}
              fontFamily="var(--font-mono), monospace"
              textAnchor="middle"
            >
              {`-${candles.length - 1 - i}m`}
            </text>
          );
        })}
      </svg>
    </div>
  );
}
