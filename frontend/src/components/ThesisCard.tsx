import { useMarketStore } from '@/stores/marketStore';

export function ThesisPanel() {
  const thesis = useMarketStore((s) => s.selectedThesis);
  if (!thesis) return <div className="bg-gray-800 rounded p-4 text-gray-400">Select a stock to view thesis</div>;

  return (
    <div className="bg-gray-800 rounded p-4">
      <h2 className="text-lg font-bold mb-2">{thesis.symbol} {thesis.direction}</h2>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>Trigger: <span className="font-mono">{thesis.trigger}</span></div>
        <div>Invalidation: <span className="font-mono">{thesis.invalidation}</span></div>
        <div>T1: <span className="font-mono">{thesis.t1}</span></div>
        <div>T2: <span className="font-mono">{thesis.t2}</span></div>
        <div>Net R:R: <span className="font-bold">{thesis.net_rr.toFixed(2)}</span></div>
        <div>Grade: <span className={`font-bold ${
          thesis.grade === 'ATTRACTIVE' ? 'text-green-400' :
          thesis.grade === 'MARGINAL' ? 'text-yellow-400' : 'text-red-400'
        }`}>{thesis.grade}</span></div>
      </div>
    </div>
  );
}
