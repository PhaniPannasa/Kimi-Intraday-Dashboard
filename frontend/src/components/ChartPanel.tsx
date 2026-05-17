import { useEffect, useRef } from 'react';
import { createChart, type CandlestickData, type ISeriesApi, type SeriesType } from 'lightweight-charts';

interface ChartPanelProps {
  data: CandlestickData[];
}

export function ChartPanel({ data }: ChartPanelProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReturnType<typeof createChart> | null>(null);
  const seriesRef = useRef<ISeriesApi<SeriesType> | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: 'transparent' },
        textColor: '#d1d5db',
      },
      grid: {
        vertLines: { color: 'rgba(55, 65, 81, 0.5)' },
        horzLines: { color: 'rgba(55, 65, 81, 0.5)' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: '#374151',
      },
      timeScale: {
        borderColor: '#374151',
        timeVisible: true,
        secondsVisible: false,
      },
      autoSize: true,
    });

    chartRef.current = chart;

    const series = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderUpColor: '#10b981',
      borderDownColor: '#ef4444',
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    seriesRef.current = series;

    if (data.length > 0) {
      series.setData(data);
      chart.timeScale().fitContent();
    }

    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []); // Initialize once

  // Update data when it changes
  useEffect(() => {
    const series = seriesRef.current;
    const chart = chartRef.current;
    if (!series || !chart || data.length === 0) return;

    series.setData(data);
    chart.timeScale().fitContent();
  }, [data]);

  return (
    <div className="w-full">
      {data.length === 0 ? (
        <div className="flex min-h-[200px] items-center justify-center rounded-md border border-dashed border-[var(--border-subtle)] text-fluid-sm text-[var(--text-secondary)]">
          Select a thesis to load chart data
        </div>
      ) : (
        <div
          ref={chartContainerRef}
          className="w-full"
          style={{ aspectRatio: '16 / 9', minHeight: 250 }}
        />
      )}
    </div>
  );
}
