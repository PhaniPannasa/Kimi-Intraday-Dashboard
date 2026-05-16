import { create } from 'zustand';
import type { MarketContextFrame, RankingEntry, ThesisCard } from '@/types/api';

interface MarketState {
  context: MarketContextFrame | null;
  longRankings: RankingEntry[];
  shortRankings: RankingEntry[];
  selectedThesis: ThesisCard | null;
  wsConnected: boolean;
  setContext: (ctx: MarketContextFrame) => void;
  setRankings: (long: RankingEntry[], short: RankingEntry[]) => void;
  setSelectedThesis: (thesis: ThesisCard | null) => void;
  setWsConnected: (connected: boolean) => void;
}

export const useMarketStore = create<MarketState>((set) => ({
  context: null,
  longRankings: [],
  shortRankings: [],
  selectedThesis: null,
  wsConnected: false,
  setContext: (ctx) => set({ context: ctx }),
  setRankings: (long, short) => set({ longRankings: long, shortRankings: short }),
  setSelectedThesis: (thesis) => set({ selectedThesis: thesis }),
  setWsConnected: (connected) => set({ wsConnected: connected }),
}));
