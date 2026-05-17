import { useWebSocket } from '@/hooks/useWebSocket';
import { PipelineStatusBar } from '@/components/PipelineStatusBar';
import { RegimeBanner } from '@/components/RegimeBanner';
import { Top25Table } from '@/components/Top25Table';
import { ThesisPanel } from '@/components/ThesisCard';
import { ActiveMonitor } from '@/components/ActiveMonitor';
import { EdgePanel } from '@/components/EdgePanel';
import { ChartPanel } from '@/components/ChartPanel';
import { AlertToast } from '@/components/AlertToast';

function App() {
  useWebSocket();

  return (
    <div className="min-h-[100dvh] bg-[var(--bg-base)]">
      <header className="sticky top-0 z-50 border-b border-[var(--border-subtle)] bg-[var(--bg-base)]/90 backdrop-blur">
        <div className="mx-auto max-w-[1600px] px-[var(--space-sm)] py-[var(--space-xs)] md:px-[var(--space-md)]">
          <div className="flex items-center justify-between">
            <h1 className="text-fluid-lg font-bold tracking-tight">Intraday Engine</h1>
            <span className="text-fluid-xs text-[var(--text-tertiary)] hidden sm:inline">NSE Nifty 100 · Research Only</span>
          </div>
        </div>
      </header>

      <PipelineStatusBar />

      <main className="mx-auto max-w-[1600px] px-[var(--space-sm)] py-[var(--space-md)] md:px-[var(--space-md)] space-y-[var(--space-md)]">
        <RegimeBanner />

        {/* Rankings section */}
        <section className="grid grid-cols-1 gap-[var(--space-md)] lg:grid-cols-2">
          <Top25Table direction="long" />
          <Top25Table direction="short" />
        </section>

        {/* Middle section: Thesis + Monitor + Edge */}
        <section className="grid grid-cols-1 gap-[var(--space-md)] md:grid-cols-2 lg:grid-cols-3">
          <ThesisPanel />
          <ActiveMonitor />
          <EdgePanel />
        </section>

        {/* Chart section */}
        <section className="bg-surface-raised rounded-lg border border-[var(--border-subtle)] p-[var(--space-md)]">
          <h2 className="text-fluid-lg font-bold mb-[var(--space-sm)]">Price Chart</h2>
          <ChartPanel data={[]} />
        </section>
      </main>

      <AlertToast />
    </div>
  );
}

export default App;
