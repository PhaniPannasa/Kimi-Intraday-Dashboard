import { useRankings } from '@/hooks/useRankings';
import type { RankingEntry } from '@/types/api';

function RankingRow({ entry }: { entry: RankingEntry }) {
  return (
    <tr className="border-b border-gray-700 hover:bg-gray-800">
      <td className="p-2 font-medium">{entry.symbol}</td>
      <td className="p-2">{entry.score.toFixed(1)}</td>
      <td className="p-2">{entry.setup_type}</td>
      <td className="p-2">{entry.confluence_score}/6</td>
      <td className="p-2">{entry.net_rr.toFixed(2)}</td>
      <td className="p-2">
        <span className={`text-xs px-2 py-1 rounded ${
          entry.actionability_tier === 'Tradeable' ? 'bg-green-900 text-green-300' :
          entry.actionability_tier === 'Constrained' ? 'bg-yellow-900 text-yellow-300' :
          'bg-gray-700 text-gray-400'
        }`}>
          {entry.actionability_tier}
        </span>
      </td>
      <td className="p-2">{entry.rank_movement}</td>
    </tr>
  );
}

export function Top25Table({ direction }: { direction: 'long' | 'short' }) {
  const { data, isLoading } = useRankings(direction);

  return (
    <div className="bg-gray-800 rounded p-4">
      <h2 className="text-lg font-bold mb-3 capitalize">Top 25 {direction}</h2>
      {isLoading ? (
        <p className="text-gray-400">Loading...</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-400 border-b border-gray-600">
              <th className="p-2">Symbol</th>
              <th className="p-2">Score</th>
              <th className="p-2">Setup</th>
              <th className="p-2">Conf</th>
              <th className="p-2">Net R:R</th>
              <th className="p-2">Tier</th>
              <th className="p-2">Move</th>
            </tr>
          </thead>
          <tbody>
            {data?.map((entry) => <RankingRow key={entry.symbol} entry={entry} />)}
          </tbody>
        </table>
      )}
    </div>
  );
}
