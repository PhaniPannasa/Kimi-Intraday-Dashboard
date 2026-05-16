import { useWebSocket } from '@/hooks/useWebSocket';
import { RegimeBanner } from '@/components/RegimeBanner';
import { Top25Table } from '@/components/Top25Table';
import { ThesisPanel } from '@/components/ThesisCard';
import { ActiveMonitor } from '@/components/ActiveMonitor';
import { EdgePanel } from '@/components/EdgePanel';

function App() {
  useWebSocket();

  return (
    <div className="min-h-screen p-4 space-y-4">
      <RegimeBanner />
      <div className="grid grid-cols-2 gap-4">
        <Top25Table direction="long" />
        <Top25Table direction="short" />
      </div>
      <div className="grid grid-cols-3 gap-4">
        <ThesisPanel />
        <ActiveMonitor />
        <EdgePanel />
      </div>
    </div>
  );
}

export default App
