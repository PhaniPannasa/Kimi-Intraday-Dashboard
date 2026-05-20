import { create } from 'zustand';
import type {
  ActiveThesisEntry,
  MarketContextFrame,
  RankingEntry,
  ThesisCard,
} from '@/types/api';
import type { DataSource } from '@/lib/apiFetch';

interface InvalidatedThesis {
  thesis_id: string;
  reason: string;
  timestamp: string;
}

/**
 * Extended edge tier shape returned by GET /api/edge/tiers.
 * Wider than the TS interface EdgeTierStats — includes `label` and
 * `live_count` that the live REST response carries.
 */
export interface EdgeTierStatsExt {
  tier_id: number;
  label?: string;
  setup_type: number;
  regime: string;
  direction: string;
  sector?: number | null;
  time_bucket?: number | null;
  n: number;
  hit_rate: number;
  ci_lower: number;
  ci_upper: number;
  is_significant: boolean;
  avg_net_return: number;
  std_net_return: number;
  live_count?: number;
}

/**
 * Derive a short summary string for the WS-compatible `edgeTiers` map
 * so existing EdgePanel rendering keeps working when REST fills the data.
 */
function summariseTier(tier: EdgeTierStatsExt): string {
  if (tier.label) return tier.label;
  const pct = (tier.hit_rate * 100).toFixed(1);
  return `n=${tier.n}, hit ${pct}%`;
}

interface MarketState {
  context: MarketContextFrame | null;
  longRankings: RankingEntry[];
  shortRankings: RankingEntry[];
  selectedThesis: ThesisCard | null;
  wsConnected: boolean;
  theses: ThesisCard[];
  activeTheses: ActiveThesisEntry[];
  invalidatedTheses: InvalidatedThesis[];
  edgeTiers: Record<number, string>;
  edgeTiersFull: Record<number, EdgeTierStatsExt>;
  lastWSTimestamps: Record<string, string>;
  sources: Record<string, DataSource>;
  setContext: (ctx: MarketContextFrame) => void;
  setRankings: (long: RankingEntry[], short: RankingEntry[]) => void;
  setSelectedThesis: (thesis: ThesisCard | null) => void;
  setWsConnected: (connected: boolean) => void;
  addOrUpdateThesis: (thesis: ThesisCard) => void;
  setActiveTheses: (theses: ActiveThesisEntry[]) => void;
  invalidateThesis: (thesisId: string, reason: string) => void;
  updateEdgeTier: (tier: number, promotion: string) => void;
  setEdgeTiersBulk: (tiers: EdgeTierStatsExt[]) => void;
  setWSTimestamp: (channel: string, ts: string) => void;
  setSource: (key: string, source: DataSource) => void;
}

export const useMarketStore = create<MarketState>((set) => ({
  context: null,
  longRankings: [],
  shortRankings: [],
  selectedThesis: null,
  wsConnected: false,
  theses: [],
  activeTheses: [],
  invalidatedTheses: [],
  edgeTiers: {},
  edgeTiersFull: {},
  lastWSTimestamps: {},
  sources: {},
  setContext: (ctx) => set({ context: ctx }),
  setRankings: (long, short) => set({ longRankings: long, shortRankings: short }),
  setSelectedThesis: (thesis) => set({ selectedThesis: thesis }),
  setWsConnected: (connected) => set({ wsConnected: connected }),
  addOrUpdateThesis: (thesis) =>
    set((state) => {
      const filtered = state.theses.filter((t) => t.thesis_id !== thesis.thesis_id);
      return { theses: [...filtered, thesis] };
    }),
  setActiveTheses: (theses) => set({ activeTheses: theses }),
  invalidateThesis: (thesisId, reason) =>
    set((state) => ({
      theses: state.theses.filter((t) => t.thesis_id !== thesisId),
      invalidatedTheses: [
        ...state.invalidatedTheses,
        { thesis_id: thesisId, reason, timestamp: new Date().toISOString() },
      ],
    })),
  updateEdgeTier: (tier, promotion) =>
    set((state) => ({
      edgeTiers: { ...state.edgeTiers, [tier]: promotion },
    })),
  setEdgeTiersBulk: (tiers) =>
    set((state) => {
      const nextFull: Record<number, EdgeTierStatsExt> = { ...state.edgeTiersFull };
      const nextStr: Record<number, string> = { ...state.edgeTiers };
      for (const tier of tiers) {
        nextFull[tier.tier_id] = tier;
        // Only fill the string map if the WS hasn't already written a
        // (presumably fresher) promotion event for this tier.
        if (!(tier.tier_id in nextStr)) {
          nextStr[tier.tier_id] = summariseTier(tier);
        }
      }
      return { edgeTiersFull: nextFull, edgeTiers: nextStr };
    }),
  setWSTimestamp: (channel, ts) =>
    set((state) => ({
      lastWSTimestamps: { ...state.lastWSTimestamps, [channel]: ts },
    })),
  setSource: (key, source) =>
    set((state) => ({ sources: { ...state.sources, [key]: source } })),
}));
