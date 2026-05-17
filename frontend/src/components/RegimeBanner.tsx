import { useMarketStore } from '@/stores/marketStore';

export function RegimeBanner() {
  const ctx = useMarketStore((s) => s.context);
  if (!ctx) return <div className="p-4 bg-gray-800 rounded">Loading context...</div>;

  return (
    <div className="p-4 bg-gray-800 rounded flex items-center justify-between">
      <div className="flex gap-4">
        <span className="font-bold text-lg">{ctx.regime}</span>
        <span className="text-gray-400">{ctx.volatility_qualifier}</span>
        <span>VIX: {ctx.vix_band}</span>
        <span>Breadth: {ctx.breadth}</span>
      </div>
      <div className="text-sm text-gray-400">{ctx.time_bucket}</div>
    </div>
  );
}
