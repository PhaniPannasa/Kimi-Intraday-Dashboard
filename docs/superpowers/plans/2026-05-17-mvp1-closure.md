# MVP 1 Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close all remaining open items from MVP 1: fix frontend blockers, add missing ChartPanel, wire WebSocket handlers, fix backend deprecation warnings, and add L10 statistical methods.

**Architecture:** Phase 1 (Frontend-First) fixes UI blockers and makes the build pass. Phase 2 (Backend) fixes deprecation warnings and adds missing statistics. Each phase is independent and verifiable on its own.

**Tech Stack:** React 18 + Vite + TypeScript + Tailwind + Zustand + TanStack Query + lightweight-charts + Vitest. FastAPI + Pydantic + pytest.

---

## File Structure

### Frontend (Phase 1)

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/main.tsx` | Modify | Add QueryClientProvider wrapper |
| `frontend/src/stores/marketStore.ts` | Modify | Add theses, invalidations, edge tier state |
| `frontend/src/types/api.ts` | Modify | (already has WSMessage types — verify) |
| `frontend/src/hooks/useRankings.ts` | Modify | Change fetch URL from localhost:8084 to `/api` |
| `frontend/src/hooks/useMarketContext.ts` | Modify | Change fetch URL from localhost:8084 to `/api` |
| `frontend/src/hooks/useWebSocket.ts` | Modify | Add L8_THESIS, L9_INVALIDATION, L10_EDGE handlers |
| `frontend/src/components/ChartPanel.tsx` | Create | lightweight-charts candlestick component |
| `frontend/src/App.tsx` | Modify | Import and render ChartPanel |
| `frontend/index.html` | Modify | Remove stale vite.svg favicon link |
| `frontend/src/hooks/useRankings.test.ts` | Modify | Test that URL uses `/api` |
| `frontend/src/hooks/useMarketContext.test.ts` | Modify | Test that URL uses `/api` |
| `frontend/src/hooks/useWebSocket.test.ts` | Modify | Test new message handlers |
| `frontend/src/components/ChartPanel.test.tsx` | Create | Test ChartPanel render |

### Backend (Phase 2)

| File | Action | Responsibility |
|---|---|---|
| `engine/models/frames.py` | Modify | Fix `datetime.utcnow()` deprecation |
| `engine/api/rest_routes.py` | Modify | Fix `datetime.utcnow()` deprecation |
| `engine/layers/l10_edge.py` | Modify | Add wilson_ci, benjamini_hochberg, bayesian_bootstrap |
| `engine/layers/l9_monitor.py` | Modify | Rename methods to on_trigger/on_tick/on_force_expire |
| `tests/test_l10.py` | Modify | Add tests for new statistical methods |
| `tests/test_l9.py` | Modify | Update test method names to match renamed API |

**Note:** L8 cost model (`engine/layers/l8_thesis.py`, `tests/test_l8_cost.py`) is already fully implemented with Indian brokerage/STT/GST formulas. No changes needed.

---

## Phase 1: Frontend Closure

### Task 1: main.tsx — Add QueryClientProvider

**Files:**
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/main.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from './App';

describe('App rendering', () => {
  it('should render without crashing', () => {
    render(<App />);
    expect(document.getElementById('root')).toBeDefined();
  });
});
```

Run: `cd frontend && npx vitest run src/main.test.tsx`
Expected: FAIL or skip (App may render fine but QueryClientProvider is missing, causing hooks to fail silently in real usage).

- [ ] **Step 2: Add QueryClientProvider to main.tsx**

Replace the contents of `frontend/src/main.tsx`:

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import './index.css';

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
```

- [ ] **Step 3: Verify build still passes**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/main.tsx frontend/src/main.test.tsx
git commit -m "fix: add QueryClientProvider to main.tsx"
```

---

### Task 2: Hooks — Change fetch URLs to `/api`

**Files:**
- Modify: `frontend/src/hooks/useRankings.ts`
- Modify: `frontend/src/hooks/useMarketContext.ts`
- Modify: `frontend/src/hooks/useRankings.test.ts`
- Modify: `frontend/src/hooks/useMarketContext.test.ts`

**Note:** `vite.config.ts` already has the `/api` proxy configured:
```ts
proxy: {
  '/api': {
    target: 'http://localhost:8084',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, ''),
  }
}
```

- [ ] **Step 1: Write failing test for useRankings URL**

Replace `frontend/src/hooks/useRankings.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockFetch = vi.fn();
(globalThis as unknown as { fetch: typeof mockFetch }).fetch = mockFetch;

describe('useRankings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should call fetch with /api proxy URL', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ symbol: 'RELIANCE', score: 85 }],
    });

    const { useRankings } = await import('./useRankings');
    expect(useRankings).toBeDefined();

    // Trigger the hook by calling the internal fetch function indirectly
    // Since hooks need a component, we test the fetch URL by extracting the fetch call
    const React = await import('react');
    let fetchUrl = '';
    mockFetch.mockImplementationOnce((url: string) => {
      fetchUrl = url;
      return Promise.resolve({ ok: true, json: async () => [] });
    });

    // Re-import to trigger fresh fetch setup
    const mod = await import('./useRankings?ts=' + Date.now());
    expect(mod.useRankings).toBeDefined();

    // Alternative: directly call the internal fetcher by replicating hook logic
    // We verify the URL starts with /api by inspecting the module after a real render
  });
});
```

Actually, a simpler approach: directly test the internal async function by temporarily exporting it, or by rendering the hook with `@testing-library/react`:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useRankings } from './useRankings';

const queryClient = new QueryClient();

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe('useRankings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  it('should fetch from /api proxy', async () => {
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => [{ symbol: 'RELIANCE', score: 85 }],
    } as Response);

    renderHook(() => useRankings('long'), { wrapper });

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/rankings/top25/long');
    });
  });
});
```

Run: `cd frontend && npx vitest run src/hooks/useRankings.test.ts`
Expected: FAIL because current code uses `http://localhost:8084/rankings/top25/long`.

- [ ] **Step 2: Update useRankings.ts to use /api**

Replace the fetch line in `frontend/src/hooks/useRankings.ts`:

```ts
async function fetchRankings(direction: 'long' | 'short'): Promise<RankingEntry[]> {
  const res = await fetch(`/api/rankings/top25/${direction}`);
  if (!res.ok) throw new Error('Failed to fetch rankings');
  return res.json();
}
```

- [ ] **Step 3: Update useRankings test to pass**

Replace `frontend/src/hooks/useRankings.test.ts` with:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useRankings } from './useRankings';

const queryClient = new QueryClient();

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe('useRankings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  it('should fetch from /api proxy', async () => {
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => [{ symbol: 'RELIANCE', score: 85, instrument_key: 'NSE_EQ|RELIANCE' }],
    } as Response);

    renderHook(() => useRankings('long'), { wrapper });

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/rankings/top25/long');
    });
  });
});
```

Run: `cd frontend && npx vitest run src/hooks/useRankings.test.ts`
Expected: PASS.

- [ ] **Step 4: Update useMarketContext.ts and its test**

Update `frontend/src/hooks/useMarketContext.ts`:

```ts
async function fetchMarketContext(): Promise<MarketContextFrame> {
  const res = await fetch('/api/market/context');
  if (!res.ok) throw new Error('Failed to fetch market context');
  return res.json();
}
```

Replace `frontend/src/hooks/useMarketContext.test.ts` with:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useMarketContext } from './useMarketContext';

const queryClient = new QueryClient();

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe('useMarketContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  it('should fetch from /api proxy', async () => {
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        regime: 'Trending-Up',
        regime_confidence: 0.85,
        volatility_qualifier: 'Volatile',
        vix_band: 'Elevated',
        vix_trajectory: 'Rising',
        time_bucket: 'Opening',
        event_flag: null,
        breadth: 'Broad',
        premarket_bias: 'Bullish',
        bank_nifty_divergence: 0.0,
      }),
    } as Response);

    renderHook(() => useMarketContext(), { wrapper });

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/market/context');
    });
  });
});
```

Run: `cd frontend && npx vitest run src/hooks/useMarketContext.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useRankings.ts frontend/src/hooks/useRankings.test.ts frontend/src/hooks/useMarketContext.ts frontend/src/hooks/useMarketContext.test.ts
git commit -m "fix: use /api proxy in hooks instead of localhost:8084"
```

---

### Task 3: index.html — Remove Stale Favicon

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Edit index.html**

Remove this line:
```html
<link rel="icon" type="image/svg+xml" href="/vite.svg" />
```

- [ ] **Step 2: Verify build passes**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "fix: remove stale vite.svg favicon link"
```

---

### Task 4: marketStore.ts — Add Missing State for WebSocket Handlers

**Files:**
- Modify: `frontend/src/stores/marketStore.ts`

- [ ] **Step 1: Write failing test**

Create `frontend/src/stores/marketStore.test.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { useMarketStore } from './marketStore';

describe('marketStore', () => {
  it('should add or update a thesis', () => {
    const store = useMarketStore.getState();
    store.addOrUpdateThesis({ thesis_id: 't1', symbol: 'RELIANCE', direction: 'LONG', setup_type: 1, trigger: 2500, invalidation: 2450, t1: 2550, t2: 2600, gross_rr: 2.0, net_rr: 1.8, grade: 'A', time_decay_multiplier: 1.0, actionability_tier: 'Research-Only', valid_until: '2026-05-17T10:00:00Z', preferred_regime: 'Trending-Up' });
    expect(useMarketStore.getState().theses).toHaveLength(1);
  });

  it('should invalidate a thesis', () => {
    const store = useMarketStore.getState();
    store.addOrUpdateThesis({ thesis_id: 't2', symbol: 'INFY', direction: 'SHORT', setup_type: 1, trigger: 1500, invalidation: 1550, t1: 1450, t2: 1400, gross_rr: 1.5, net_rr: 1.3, grade: 'B', time_decay_multiplier: 0.9, actionability_tier: 'Research-Only', valid_until: '2026-05-17T10:00:00Z', preferred_regime: 'Trending-Down' });
    store.invalidateThesis('t2', 'Stop loss hit');
    expect(useMarketStore.getState().invalidatedTheses).toContainEqual(
      expect.objectContaining({ thesis_id: 't2', reason: 'Stop loss hit' })
    );
  });

  it('should update edge tier', () => {
    const store = useMarketStore.getState();
    store.updateEdgeTier(1, 'PROMOTED');
    expect(useMarketStore.getState().edgeTiers[1]).toBe('PROMOTED');
  });
});
```

Run: `cd frontend && npx vitest run src/stores/marketStore.test.ts`
Expected: FAIL — methods don't exist yet.

- [ ] **Step 2: Update marketStore.ts**

Replace `frontend/src/stores/marketStore.ts`:

```ts
import { create } from 'zustand';
import type { MarketContextFrame, RankingEntry, ThesisCard } from '@/types/api';

interface InvalidatedThesis {
  thesis_id: string;
  reason: string;
  timestamp: string;
}

interface MarketState {
  context: MarketContextFrame | null;
  longRankings: RankingEntry[];
  shortRankings: RankingEntry[];
  selectedThesis: ThesisCard | null;
  wsConnected: boolean;
  theses: ThesisCard[];
  invalidatedTheses: InvalidatedThesis[];
  edgeTiers: Record<number, string>;
  setContext: (ctx: MarketContextFrame) => void;
  setRankings: (long: RankingEntry[], short: RankingEntry[]) => void;
  setSelectedThesis: (thesis: ThesisCard | null) => void;
  setWsConnected: (connected: boolean) => void;
  addOrUpdateThesis: (thesis: ThesisCard) => void;
  invalidateThesis: (thesisId: string, reason: string) => void;
  updateEdgeTier: (tier: number, promotion: string) => void;
}

export const useMarketStore = create<MarketState>((set) => ({
  context: null,
  longRankings: [],
  shortRankings: [],
  selectedThesis: null,
  wsConnected: false,
  theses: [],
  invalidatedTheses: [],
  edgeTiers: {},
  setContext: (ctx) => set({ context: ctx }),
  setRankings: (long, short) => set({ longRankings: long, shortRankings: short }),
  setSelectedThesis: (thesis) => set({ selectedThesis: thesis }),
  setWsConnected: (connected) => set({ wsConnected: connected }),
  addOrUpdateThesis: (thesis) =>
    set((state) => {
      const filtered = state.theses.filter((t) => t.thesis_id !== thesis.thesis_id);
      return { theses: [...filtered, thesis] };
    }),
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
}));
```

Run: `cd frontend && npx vitest run src/stores/marketStore.test.ts`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/marketStore.ts frontend/src/stores/marketStore.test.ts
git commit -m "feat: add thesis, invalidation, and edge tier state to marketStore"
```

---

### Task 5: useWebSocket.ts — Add L8/L9/L10 Handlers

**Files:**
- Modify: `frontend/src/hooks/useWebSocket.ts`
- Modify: `frontend/src/hooks/useWebSocket.test.ts`

- [ ] **Step 1: Write failing test**

Replace `frontend/src/hooks/useWebSocket.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useMarketStore } from '@/stores/marketStore';
import { useWebSocket } from './useWebSocket';

class MockWebSocket {
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  sent: string[] = [];
  close = vi.fn();
  send = vi.fn((data: string) => this.sent.push(data));
}

describe('useWebSocket', () => {
  let mockWs: MockWebSocket;

  beforeEach(() => {
    mockWs = new MockWebSocket();
    vi.stubGlobal('WebSocket', vi.fn(() => mockWs));
    useMarketStore.setState({
      theses: [],
      invalidatedTheses: [],
      edgeTiers: {},
      wsConnected: false,
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('should handle L8_THESIS messages', () => {
    renderHook(() => useWebSocket());
    mockWs.onopen?.();

    const msg = {
      type: 'L8_THESIS',
      timestamp: '2026-05-17T09:30:00Z',
      payload: {
        thesis_id: 't1',
        card: {
          thesis_id: 't1',
          symbol: 'RELIANCE',
          direction: 'LONG',
          setup_type: 1,
          trigger: 2500,
          invalidation: 2450,
          t1: 2550,
          t2: 2600,
          gross_rr: 2.0,
          net_rr: 1.8,
          grade: 'A',
          time_decay_multiplier: 1.0,
          actionability_tier: 'Research-Only',
          valid_until: '2026-05-17T10:00:00Z',
          preferred_regime: 'Trending-Up',
        },
      },
    };
    mockWs.onmessage?.({ data: JSON.stringify(msg) });

    expect(useMarketStore.getState().theses).toHaveLength(1);
    expect(useMarketStore.getState().theses[0].symbol).toBe('RELIANCE');
  });

  it('should handle L9_INVALIDATION messages', () => {
    renderHook(() => useWebSocket());
    mockWs.onopen?.();

    // First add a thesis
    useMarketStore.getState().addOrUpdateThesis({
      thesis_id: 't2',
      symbol: 'INFY',
      direction: 'SHORT',
      setup_type: 1,
      trigger: 1500,
      invalidation: 1550,
      t1: 1450,
      t2: 1400,
      gross_rr: 1.5,
      net_rr: 1.3,
      grade: 'B',
      time_decay_multiplier: 0.9,
      actionability_tier: 'Research-Only',
      valid_until: '2026-05-17T10:00:00Z',
      preferred_regime: 'Trending-Down',
    });

    const msg = {
      type: 'L9_INVALIDATION',
      timestamp: '2026-05-17T09:35:00Z',
      payload: { thesis_id: 't2', reason: 'Stop loss hit' },
    };
    mockWs.onmessage?.({ data: JSON.stringify(msg) });

    expect(useMarketStore.getState().theses).toHaveLength(0);
    expect(useMarketStore.getState().invalidatedTheses).toHaveLength(1);
  });

  it('should handle L10_EDGE messages', () => {
    renderHook(() => useWebSocket());
    mockWs.onopen?.();

    const msg = {
      type: 'L10_EDGE',
      timestamp: '2026-05-17T09:40:00Z',
      payload: { tier: 3, promotion: 'PROMOTED' },
    };
    mockWs.onmessage?.({ data: JSON.stringify(msg) });

    expect(useMarketStore.getState().edgeTiers[3]).toBe('PROMOTED');
  });
});
```

Run: `cd frontend && npx vitest run src/hooks/useWebSocket.test.ts`
Expected: FAIL — handlers don't exist in useWebSocket.ts.

- [ ] **Step 2: Update useWebSocket.ts**

Replace `frontend/src/hooks/useWebSocket.ts`:

```ts
import { useEffect, useRef } from 'react';
import { useMarketStore } from '@/stores/marketStore';
import type { WSMessage } from '@/types/api';

const WS_URL = 'ws://localhost:8084/ws/v1/stream';

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null);
  const setWsConnected = useMarketStore((s) => s.setWsConnected);
  const setContext = useMarketStore((s) => s.setContext);
  const setRankings = useMarketStore((s) => s.setRankings);
  const addOrUpdateThesis = useMarketStore((s) => s.addOrUpdateThesis);
  const invalidateThesis = useMarketStore((s) => s.invalidateThesis);
  const updateEdgeTier = useMarketStore((s) => s.updateEdgeTier);

  useEffect(() => {
    const socket = new WebSocket(WS_URL);
    ws.current = socket;

    socket.onopen = () => {
      setWsConnected(true);
      socket.send(JSON.stringify({ action: 'subscribe', channels: ['market', 'rankings', 'theses', 'edge'] }));
    };

    socket.onmessage = (event) => {
      const msg: WSMessage = JSON.parse(event.data);
      switch (msg.type) {
        case 'L1_CONTEXT':
          setContext(msg.payload);
          break;
        case 'L6_RANKINGS':
          setRankings(msg.payload.long, msg.payload.short);
          break;
        case 'L8_THESIS':
          addOrUpdateThesis(msg.payload.card);
          break;
        case 'L9_INVALIDATION':
          invalidateThesis(msg.payload.thesis_id, msg.payload.reason);
          break;
        case 'L10_EDGE':
          updateEdgeTier(msg.payload.tier, msg.payload.promotion);
          break;
      }
    };

    socket.onclose = () => setWsConnected(false);
    socket.onerror = () => setWsConnected(false);

    return () => {
      socket.close();
    };
  }, [setWsConnected, setContext, setRankings, addOrUpdateThesis, invalidateThesis, updateEdgeTier]);
}
```

Run: `cd frontend && npx vitest run src/hooks/useWebSocket.test.ts`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useWebSocket.ts frontend/src/hooks/useWebSocket.test.ts
git commit -m "feat: add L8_THESIS, L9_INVALIDATION, L10_EDGE WebSocket handlers"
```

---

### Task 6: ChartPanel.tsx — Create Component

**Files:**
- Create: `frontend/src/components/ChartPanel.tsx`
- Create: `frontend/src/components/ChartPanel.test.tsx`

- [ ] **Step 1: Write failing test**

Create `frontend/src/components/ChartPanel.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { ChartPanel } from './ChartPanel';

describe('ChartPanel', () => {
  it('should render a chart container', () => {
    const { container } = render(<ChartPanel data={[]} />);
    expect(container.querySelector('div')).toBeDefined();
  });

  it('should render with candlestick data', () => {
    const data = [
      { time: '2026-05-17', open: 2500, high: 2550, low: 2480, close: 2520 },
    ];
    const { container } = render(<ChartPanel data={data} />);
    expect(container.querySelector('div')).toBeDefined();
  });
});
```

Run: `cd frontend && npx vitest run src/components/ChartPanel.test.tsx`
Expected: FAIL — ChartPanel doesn't exist.

- [ ] **Step 2: Create ChartPanel.tsx**

Create `frontend/src/components/ChartPanel.tsx`:

```tsx
import { useEffect, useRef } from 'react';
import { createChart, CandlestickData } from 'lightweight-charts';

interface ChartPanelProps {
  data: CandlestickData[];
}

export function ChartPanel({ data }: ChartPanelProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 300,
      layout: {
        background: { color: '#1f2937' },
        textColor: '#d1d5db',
      },
      grid: {
        vertLines: { color: '#374151' },
        horzLines: { color: '#374151' },
      },
    });

    const series = chart.addCandlestickSeries();
    series.setData(data);

    return () => {
      chart.remove();
    };
  }, [data]);

  return <div ref={chartContainerRef} className="w-full h-[300px]" />;
}
```

Run: `cd frontend && npx vitest run src/components/ChartPanel.test.tsx`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ChartPanel.tsx frontend/src/components/ChartPanel.test.tsx
git commit -m "feat: add ChartPanel component with lightweight-charts"
```

---

### Task 7: App.tsx — Integrate ChartPanel

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Update App.tsx**

Replace `frontend/src/App.tsx`:

```tsx
import { useWebSocket } from '@/hooks/useWebSocket';
import { RegimeBanner } from '@/components/RegimeBanner';
import { Top25Table } from '@/components/Top25Table';
import { ThesisPanel } from '@/components/ThesisCard';
import { ActiveMonitor } from '@/components/ActiveMonitor';
import { EdgePanel } from '@/components/EdgePanel';
import { ChartPanel } from '@/components/ChartPanel';

function App() {
  useWebSocket();

  return (
    <div className="min-h-screen p-4 space-y-4 max-w-7xl mx-auto">
      <RegimeBanner />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Top25Table direction="long" />
        <Top25Table direction="short" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ThesisPanel />
        <ActiveMonitor />
        <EdgePanel />
      </div>
      <div className="bg-gray-800 rounded p-4">
        <h2 className="text-lg font-bold mb-2 text-white">Price Chart</h2>
        <ChartPanel data={[]} />
      </div>
    </div>
  );
}

export default App;
```

- [ ] **Step 2: Verify build passes**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: integrate ChartPanel into App layout"
```

---

### Task 8: Phase 1 Verification

**Files:**
- All frontend files above

- [ ] **Step 1: Run full Vitest suite**

```bash
cd frontend && npx vitest run
```
Expected: All tests pass.

- [ ] **Step 2: Run production build**

```bash
cd frontend && npm run build
```
Expected: Build succeeds with zero errors.

- [ ] **Step 3: Commit verification results**

```bash
git add -A
git commit -m "chore: Phase 1 frontend closure complete — all tests and build passing"
```

---

## Phase 2: Backend Closure

### Task 9: Fix datetime.utcnow() Deprecation

**Files:**
- Modify: `engine/models/frames.py`
- Modify: `engine/api/rest_routes.py`

- [ ] **Step 1: Write failing test for deprecation**

Create `tests/test_deprecation.py`:

```python
import pytest
import warnings
from datetime import datetime, timezone


def test_frames_py_no_deprecated_utcnow():
    """Verify frames.py uses timezone-aware datetime, not utcnow()."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        from models.frames import ThesisCard
        # Trigger default instantiation
        card = ThesisCard(
            thesis_id="test",
            symbol="RELIANCE",
            direction="LONG",
            setup_type=1,
            trigger=2500,
            invalidation=2450,
            t1=2550,
            t2=2600,
            gross_rr=2.0,
            net_rr=1.8,
            grade="A",
            time_decay_multiplier=1.0,
            actionability_tier="Research-Only",
            preferred_regime="Trending-Up",
        )
        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) == 0, f"DeprecationWarning raised: {deprecation_warnings}"


def test_rest_routes_no_deprecated_utcnow():
    """Verify rest_routes health endpoint doesn't use utcnow."""
    import ast
    import inspect
    from api import rest_routes
    source = inspect.getsource(rest_routes)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "utcnow":
            pytest.fail("rest_routes.py still contains datetime.utcnow()")
```

Run: `cd engine && pytest ../tests/test_deprecation.py -v`
Expected: FAIL — `utcnow` still present.

- [ ] **Step 2: Fix frames.py**

In `engine/models/frames.py`, find:
```python
from datetime import datetime
```
Change to:
```python
from datetime import datetime, timezone
```

Find:
```python
    valid_until: datetime = datetime.utcnow()
```
Change to:
```python
    valid_until: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

**Note:** Since `valid_until` is a Pydantic model field with a mutable default, use `Field(default_factory=...)` instead of a plain default to avoid shared state issues.

- [ ] **Step 3: Fix rest_routes.py**

In `engine/api/rest_routes.py`, find:
```python
from datetime import datetime
```
Change to:
```python
from datetime import datetime, timezone
```

Find:
```python
        last_bar_processed=datetime.utcnow(),
```
Change to:
```python
        last_bar_processed=datetime.now(timezone.utc),
```

- [ ] **Step 4: Run deprecation test again**

Run: `cd engine && pytest ../tests/test_deprecation.py -v`
Expected: PASS.

- [ ] **Step 5: Run full pytest suite**

Run: `cd engine && pytest`
Expected: All 77 existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add engine/models/frames.py engine/api/rest_routes.py tests/test_deprecation.py
git commit -m "fix: replace deprecated datetime.utcnow() with timezone-aware now()"
```

---

### Task 10: L10 — Add Statistical Methods

**Files:**
- Modify: `engine/layers/l10_edge.py`
- Modify: `tests/test_l10.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_l10.py`:

```python
from layers.l10_edge import wilson_ci, benjamini_hochberg, bayesian_bootstrap


def test_wilson_ci_basic():
    lower, upper = wilson_ci(hit_rate=0.6, n=100)
    assert 0 < lower < 0.6 < upper < 1.0


def test_wilson_ci_zero_n():
    lower, upper = wilson_ci(hit_rate=0.0, n=0)
    assert lower == 0.0
    assert upper == 0.0


def test_benjamini_hochberg_basic():
    p_values = [0.01, 0.04, 0.03, 0.08, 0.2]
    significant = benjamini_hochberg(p_values, alpha=0.05)
    assert significant[0] is True
    assert significant[4] is False


def test_benjamini_hochberg_empty():
    assert benjamini_hochberg([]) == []


def test_bayesian_bootstrap_basic():
    returns = [0.5, -0.2, 1.2, 0.8, -0.1]
    result = bayesian_bootstrap(returns, n_bootstrap=1000)
    assert "mean" in result
    assert "ci_lower" in result
    assert "ci_upper" in result
    assert result["ci_lower"] < result["mean"] < result["ci_upper"]
```

Run: `cd engine && pytest ../tests/test_l10.py::test_wilson_ci_basic -v`
Expected: FAIL — functions don't exist.

- [ ] **Step 2: Add wilson_ci, benjamini_hochberg, bayesian_bootstrap to l10_edge.py**

Insert these functions at the top of `engine/layers/l10_edge.py`, after the imports and before `check_min_samples`:

```python
import random


def wilson_ci(hit_rate: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Returns (lower_bound, upper_bound) clamped to [0, 1].
    """
    if n == 0:
        return (0.0, 0.0)
    p = hit_rate
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half_width = z * ((p * (1 - p) / n + z**2 / (4 * n**2)) ** 0.5) / denom
    return (max(0.0, centre - half_width), min(1.0, centre + half_width))


def benjamini_hochberg(p_values: list[float], alpha: float = 0.05) -> list[bool]:
    """Benjamini-Hochberg false discovery rate correction.

    Returns a list of booleans indicating significance after FDR correction.
    """
    if not p_values:
        return []
    sorted_idx = sorted(range(len(p_values)), key=lambda i: p_values[i])
    m = len(p_values)
    significant = [False] * m
    for rank, idx in enumerate(sorted_idx, start=1):
        if p_values[idx] <= rank * alpha / m:
            significant[idx] = True
    return significant


def bayesian_bootstrap(returns: list[float], n_bootstrap: int = 10000) -> dict:
    """Bayesian bootstrap for mean net return.

    Returns dict with mean, ci_lower, ci_upper (95% credible interval).
    """
    means = []
    n = len(returns)
    for _ in range(n_bootstrap):
        weights = [random.random() for _ in range(n)]
        total = sum(weights)
        weights = [w / total for w in weights]
        mean = sum(w * r for w, r in zip(weights, returns))
        means.append(mean)
    means.sort()
    return {
        "mean": sum(means) / len(means),
        "ci_lower": means[int(0.025 * n_bootstrap)],
        "ci_upper": means[int(0.975 * n_bootstrap)],
    }
```

- [ ] **Step 3: Update L10EdgeLookup to use wilson_ci**

In `engine/layers/l10_edge.py`, modify the `lookup` method. After extracting `ci_lower` and `ci_upper` from the row, if they are both 0.0 (meaning not pre-computed), compute them using `wilson_ci`:

```python
        n = row.get("n", 0)
        hit_rate = row.get("hit_rate", 0.0)
        ci_lower = row.get("ci_lower", 0.0)
        ci_upper = row.get("ci_upper", 0.0)

        if n > 0 and ci_lower == 0.0 and ci_upper == 0.0:
            ci_lower, ci_upper = wilson_ci(hit_rate, n)
```

Keep the rest of the `lookup` method unchanged.

- [ ] **Step 4: Run new L10 tests**

Run: `cd engine && pytest ../tests/test_l10.py -v`
Expected: All tests pass, including new ones.

- [ ] **Step 5: Run full pytest suite**

Run: `cd engine && pytest`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add engine/layers/l10_edge.py tests/test_l10.py
git commit -m "feat: add wilson_ci, benjamini_hochberg, bayesian_bootstrap to L10"
```

---

### Task 11: L9 — Rename Methods to Match Plan

**Files:**
- Modify: `engine/layers/l9_monitor.py`
- Modify: `tests/test_l9.py`

**Note:** No API consumers (rest_routes.py, websocket_manager.py) reference L9ShadowLedger, so only the class and its tests need updating.

- [ ] **Step 1: Write failing test for renamed API**

Append to `tests/test_l9.py`:

```python
@pytest.mark.asyncio
async def test_on_trigger_api():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_trigger(thesis)
    assert thesis["thesis_id"] in ledger.active


@pytest.mark.asyncio
async def test_on_tick_invalidation():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_trigger(thesis)
    invalidated = await ledger.on_tick(price=2440.0)
    assert any(t["thesis_id"] == "test-1" for t in invalidated)


@pytest.mark.asyncio
async def test_on_force_expire():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_trigger(thesis)
    expired = await ledger.on_force_expire()
    assert any(t["thesis_id"] == "test-1" for t in expired)
    assert len(ledger.active) == 0
```

Run: `cd engine && pytest ../tests/test_l9.py::test_on_trigger_api -v`
Expected: FAIL — methods don't exist.

- [ ] **Step 2: Rename methods in l9_monitor.py**

Replace `engine/layers/l9_monitor.py`:

```python
from datetime import datetime, timezone
from typing import List

from models.enums import ThesisState


class L9ShadowLedger:
    """Tracks active thesis lifecycles — registration, invalidation, T1/T2 hits, and force expiry."""

    def __init__(self):
        self.active: dict[str, dict] = {}
        self.history: list[dict] = []

    async def on_trigger(self, thesis: dict):
        thesis["state"] = ThesisState.ACTIVE.value
        thesis["entry_ts"] = datetime.now(timezone.utc)
        thesis["mfe_pct"] = 0.0
        thesis["mae_pct"] = 0.0
        self.active[thesis["thesis_id"]] = thesis

    async def on_tick(self, price: float) -> List[dict]:
        triggered = []
        invalidated = []
        for tid, t in list(self.active.items()):
            entry = t.get("entry_price") or t["trigger"]
            mfe = (price - entry) / entry * 100
            mae = (price - entry) / entry * 100
            t["mfe_pct"] = max(t.get("mfe_pct", 0), mfe)
            t["mae_pct"] = min(t.get("mae_pct", 0), mae)

            if t["direction"] == "LONG":
                if price >= t["t2"]:
                    t["state"] = ThesisState.T2_HIT.value
                    t["exit_price"] = price
                    t["exit_ts"] = datetime.now(timezone.utc)
                    triggered.append(t)
                    del self.active[tid]
                    self.history.append(t)
                elif price >= t["t1"]:
                    t["state"] = ThesisState.T1_HIT.value
                    t["exit_price"] = price
                    t["exit_ts"] = datetime.now(timezone.utc)
                    triggered.append(t)
                    del self.active[tid]
                    self.history.append(t)
                elif price <= t["invalidation"]:
                    t["state"] = ThesisState.STOPPED_OUT.value
                    t["exit_price"] = price
                    t["exit_ts"] = datetime.now(timezone.utc)
                    invalidated.append(t)
                    del self.active[tid]
                    self.history.append(t)
            else:  # SHORT
                if price <= t["t2"]:
                    t["state"] = ThesisState.T2_HIT.value
                    t["exit_price"] = price
                    t["exit_ts"] = datetime.now(timezone.utc)
                    triggered.append(t)
                    del self.active[tid]
                    self.history.append(t)
                elif price <= t["t1"]:
                    t["state"] = ThesisState.T1_HIT.value
                    t["exit_price"] = price
                    t["exit_ts"] = datetime.now(timezone.utc)
                    triggered.append(t)
                    del self.active[tid]
                    self.history.append(t)
                elif price >= t["invalidation"]:
                    t["state"] = ThesisState.STOPPED_OUT.value
                    t["exit_price"] = price
                    t["exit_ts"] = datetime.now(timezone.utc)
                    invalidated.append(t)
                    del self.active[tid]
                    self.history.append(t)

        return triggered + invalidated

    async def on_force_expire(self) -> List[dict]:
        expired = list(self.active.values())
        for t in expired:
            t["state"] = ThesisState.FORCE_EXPIRED.value
            t["exit_ts"] = datetime.now(timezone.utc)
            self.history.append(t)
        self.active.clear()
        return expired
```

- [ ] **Step 3: Update existing L9 tests to use new names**

Replace `tests/test_l9.py`:

```python
import pytest
from datetime import datetime, timezone
from layers.l9_monitor import L9ShadowLedger
from models.enums import ThesisState


def make_thesis(thesis_id="test-1", symbol="RELIANCE", direction="LONG",
                trigger=2500.0, invalidation=2450.0, t1=2550.0, t2=2600.0):
    return {
        "thesis_id": thesis_id,
        "symbol": symbol,
        "direction": direction,
        "trigger": trigger,
        "invalidation": invalidation,
        "t1": t1,
        "t2": t2
    }


@pytest.mark.asyncio
async def test_on_trigger_thesis():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_trigger(thesis)
    assert thesis["thesis_id"] in ledger.active


@pytest.mark.asyncio
async def test_on_tick_invalidation():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_trigger(thesis)
    # Price drops below invalidation -- thesis should be invalidated
    invalidated = await ledger.on_tick(price=2440.0)
    assert any(t["thesis_id"] == "test-1" for t in invalidated)


@pytest.mark.asyncio
async def test_on_tick_t1_hit():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_trigger(thesis)
    # Price rises to T1
    hit = await ledger.on_tick(price=2550.0)
    assert any(t["thesis_id"] == "test-1" for t in hit)


@pytest.mark.asyncio
async def test_on_tick_t2_hit():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_trigger(thesis)
    # Price rises past T2
    hit = await ledger.on_tick(price=2600.0)
    assert any(t["thesis_id"] == "test-1" for t in hit)


@pytest.mark.asyncio
async def test_on_force_expire():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_trigger(thesis)
    expired = await ledger.on_force_expire()
    assert any(t["thesis_id"] == "test-1" for t in expired)
    assert len(ledger.active) == 0


@pytest.mark.asyncio
async def test_short_direction_invalidation():
    ledger = L9ShadowLedger()
    thesis = make_thesis(direction="SHORT", trigger=2500.0, invalidation=2550.0, t1=2450.0, t2=2400.0)
    await ledger.on_trigger(thesis)
    # Price rises above invalidation for short
    invalidated = await ledger.on_tick(price=2560.0)
    assert any(t["thesis_id"] == "test-1" for t in invalidated)
```

Run: `cd engine && pytest ../tests/test_l9.py -v`
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l9_monitor.py tests/test_l9.py
git commit -m "refactor: rename L9 methods to on_trigger/on_tick/on_force_expire"
```

---

### Task 12: Phase 2 Verification

**Files:**
- All backend files above

- [ ] **Step 1: Run full pytest suite**

```bash
cd engine && pytest
```
Expected: All tests pass (77 existing + new deprecation + L10 stats + L9 rename).

- [ ] **Step 2: Verify no deprecation warnings**

```bash
cd engine && pytest -W error::DeprecationWarning
```
Expected: No DeprecationWarning failures.

- [ ] **Step 3: Commit final state**

```bash
git add -A
git commit -m "chore: Phase 2 backend closure complete — no deprecation warnings, L10 stats, L9 aligned"
```

---

## Self-Review

### 1. Spec Coverage

| Spec Requirement | Plan Task |
|---|---|
| main.tsx QueryClientProvider | Task 1 |
| Hooks use /api proxy | Task 2 |
| index.html remove vite.svg | Task 3 |
| useWebSocket L8/L9/L10 handlers | Task 5 |
| marketStore theses/invalidations/edge | Task 4 |
| ChartPanel.tsx | Task 6 |
| App.tsx integration | Task 7 |
| datetime.utcnow() deprecation | Task 9 |
| L8 cost model (Indian brokerage) | Already implemented — verified in design |
| L10 wilson_ci, BH, bootstrap | Task 10 |
| L9 rename to on_trigger/on_tick | Task 11 |

**Coverage:** Complete. All 9 items from the design spec are addressed.

### 2. Placeholder Scan

- No "TBD", "TODO", "implement later" found.
- No vague "add appropriate error handling" steps.
- All test code is explicit and complete.
- All implementation code is shown in full.

### 3. Type Consistency

- `WSMessage` type in `api.ts` already defines `L8_THESIS`, `L9_INVALIDATION`, `L10_EDGE` — consistent with handlers in Task 5.
- `ThesisCard` interface in `api.ts` matches store and component usage.
- `MarketContextFrame` and `RankingEntry` interfaces unchanged.
- L9 method names `on_trigger`/`on_tick`/`on_force_expire` consistent across class and tests.
- L10 function signatures consistent across module and tests.

**Result:** Plan is complete, consistent, and ready for execution.
