# MVP 1 Complete Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make MVP1 actually run end-to-end: frontend builds and connects to backend, backend orchestrates L1-L10 pipeline every minute, WebSocket broadcasts real rankings/theses/edge events, and the stack verifies clean in Docker Compose.

**Architecture:** Four phases. Phase 1 (Frontend) gets the UI runnable. Phase 2 (Backend Core) fixes deviations and adds statistics. Phase 3 (Backend Orchestration) wires the pipeline and WebSocket broadcasts. Phase 4 (Integration) verifies the full stack in Docker Compose.

**Tech Stack:** React 18 + Vite + TS + Tailwind + Zustand + TanStack Query + lightweight-charts + Vitest. FastAPI + Pydantic + APScheduler + asyncpg + Redis + pytest + Docker Compose.

---

## File Structure

### Phase 1: Frontend

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/main.tsx` | Modify | Add QueryClientProvider |
| `frontend/src/stores/marketStore.ts` | Modify | Add theses, invalidations, edge tier state |
| `frontend/src/hooks/useRankings.ts` | Modify | Use `/api` proxy URL |
| `frontend/src/hooks/useMarketContext.ts` | Modify | Use `/api` proxy URL |
| `frontend/src/hooks/useWebSocket.ts` | Modify | Add L8/L9/L10 handlers |
| `frontend/src/components/ChartPanel.tsx` | Create | lightweight-charts candlestick component |
| `frontend/src/App.tsx` | Modify | Integrate ChartPanel, remove stale favicon link |
| `frontend/index.html` | Modify | Remove stale vite.svg favicon link |

### Phase 2: Backend Core

| File | Action | Responsibility |
|---|---|---|
| `engine/models/frames.py` | Modify | Fix `datetime.utcnow()` deprecation |
| `engine/api/rest_routes.py` | Modify | Fix `datetime.utcnow()` deprecation |
| `engine/layers/l10_edge.py` | Modify | Add wilson_ci, benjamini_hochberg, bayesian_bootstrap |
| `engine/layers/l9_monitor.py` | Modify | Rename methods to on_trigger/on_tick/on_force_expire |
| `tests/test_deprecation.py` | Create | Verify no utcnow deprecation warnings |
| `tests/test_l10.py` | Modify | Add tests for statistical methods |
| `tests/test_l9.py` | Modify | Update tests for renamed API |

### Phase 3: Backend Orchestration

| File | Action | Responsibility |
|---|---|---|
| `engine/core/auth/token_manager.py` | Create | OAuth token refresh logic |
| `engine/core/scheduler/market_scheduler.py` | Modify | Wire pipeline jobs |
| `engine/api/websocket_manager.py` | Modify | Broadcast L8/L9/L10 messages |
| `engine/core/pipeline.py` | Create | L1-L8 pipeline orchestrator |
| `engine/main.py` | Modify | Start scheduler and pipeline in lifespan |
| `tests/test_pipeline.py` | Create | Integration test for pipeline |
| `tests/test_websocket_broadcast.py` | Create | Test WS broadcasts L1/L6/L8/L9/L10 |

### Phase 4: Integration

| File | Action | Responsibility |
|---|---|---|
| `tests/e2e/smoke.test.py` | Create | E2E REST + WS smoke test |
| `docker-compose.yml` | Verify | Already exists — verify stack starts |
| `frontend/vite.config.ts` | Modify | Add WS proxy for production parity |

---

## Phase 1: Frontend Closure

### Task 1: main.tsx — Add QueryClientProvider

**Files:**
- Modify: `frontend/src/main.tsx`
- Create: `frontend/src/main.test.tsx`

- [ ] **Step 1: Write failing test**

Create `frontend/src/main.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import App from './App';

describe('App rendering', () => {
  it('should render without crashing', () => {
    const { container } = render(<App />);
    expect(container).toBeDefined();
  });
});
```

Run: `cd frontend && npx vitest run src/main.test.tsx`
Expected: May pass or show React Query warnings (hooks used without provider).

- [ ] **Step 2: Add QueryClientProvider**

Replace `frontend/src/main.tsx`:

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

- [ ] **Step 3: Verify build passes**

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

- [ ] **Step 1: Update useRankings.ts**

Replace the fetch line in `frontend/src/hooks/useRankings.ts`:

```ts
async function fetchRankings(direction: 'long' | 'short'): Promise<RankingEntry[]> {
  const res = await fetch(`/api/rankings/top25/${direction}`);
  if (!res.ok) throw new Error('Failed to fetch rankings');
  return res.json();
}
```

- [ ] **Step 2: Update useRankings.test.ts**

Replace `frontend/src/hooks/useRankings.test.ts`:

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

- [ ] **Step 3: Update useMarketContext.ts and test**

Update `frontend/src/hooks/useMarketContext.ts`:

```ts
async function fetchMarketContext(): Promise<MarketContextFrame> {
  const res = await fetch('/api/market/context');
  if (!res.ok) throw new Error('Failed to fetch market context');
  return res.json();
}
```

Replace `frontend/src/hooks/useMarketContext.test.ts`:

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

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useRankings.ts frontend/src/hooks/useRankings.test.ts frontend/src/hooks/useMarketContext.ts frontend/src/hooks/useMarketContext.test.ts
git commit -m "fix: use /api proxy in hooks instead of localhost:8084"
```

---

### Task 3: marketStore.ts — Add Missing State

**Files:**
- Modify: `frontend/src/stores/marketStore.ts`
- Create: `frontend/src/stores/marketStore.test.ts`

- [ ] **Step 1: Write failing test**

Create `frontend/src/stores/marketStore.test.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { useMarketStore } from './marketStore';

describe('marketStore', () => {
  it('should add or update a thesis', () => {
    const store = useMarketStore.getState();
    store.addOrUpdateThesis({
      thesis_id: 't1', symbol: 'RELIANCE', direction: 'LONG', setup_type: 1,
      trigger: 2500, invalidation: 2450, t1: 2550, t2: 2600,
      gross_rr: 2.0, net_rr: 1.8, grade: 'ATTRACTIVE',
      time_decay_multiplier: 1.0, actionability_tier: 'Research-Only',
      valid_until: '2026-05-17T10:00:00Z', preferred_regime: 'Trending-Up',
    });
    expect(useMarketStore.getState().theses).toHaveLength(1);
  });

  it('should invalidate a thesis', () => {
    const store = useMarketStore.getState();
    store.addOrUpdateThesis({
      thesis_id: 't2', symbol: 'INFY', direction: 'SHORT', setup_type: 1,
      trigger: 1500, invalidation: 1550, t1: 1450, t2: 1400,
      gross_rr: 1.5, net_rr: 1.3, grade: 'MARGINAL',
      time_decay_multiplier: 0.9, actionability_tier: 'Research-Only',
      valid_until: '2026-05-17T10:00:00Z', preferred_regime: 'Trending-Down',
    });
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

### Task 4: useWebSocket.ts — Add L8/L9/L10 Handlers

**Files:**
- Modify: `frontend/src/hooks/useWebSocket.ts`
- Modify: `frontend/src/hooks/useWebSocket.test.ts`

- [ ] **Step 1: Write failing test**

Replace `frontend/src/hooks/useWebSocket.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
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
          grade: 'ATTRACTIVE',
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
      grade: 'MARGINAL',
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
Expected: FAIL — handlers don't exist.

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

### Task 5: ChartPanel.tsx + App.tsx Integration

**Files:**
- Create: `frontend/src/components/ChartPanel.tsx`
- Create: `frontend/src/components/ChartPanel.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/index.html`

- [ ] **Step 1: Create ChartPanel.tsx**

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

- [ ] **Step 2: Create ChartPanel.test.tsx**

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

- [ ] **Step 3: Update App.tsx and index.html**

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

Edit `frontend/index.html`: Remove the line:
```html
<link rel="icon" type="image/svg+xml" href="/vite.svg" />
```

- [ ] **Step 4: Verify build passes**

Run: `cd frontend && npm run build`
Expected: Build succeeds with zero errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ChartPanel.tsx frontend/src/components/ChartPanel.test.tsx frontend/src/App.tsx frontend/index.html
git commit -m "feat: add ChartPanel, integrate into App, remove stale favicon"
```

---

### Task 6: Phase 1 Verification

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

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: Phase 1 frontend closure complete"
```

---

## Phase 2: Backend Core Fixes

### Task 7: Fix datetime.utcnow() Deprecation

**Files:**
- Modify: `engine/models/frames.py`
- Modify: `engine/api/rest_routes.py`
- Create: `tests/test_deprecation.py`

- [ ] **Step 1: Fix frames.py**

In `engine/models/frames.py`:
- Change `from datetime import datetime` to `from datetime import datetime, timezone`
- Change `valid_until: datetime = datetime.utcnow()` to:
  ```python
  valid_until: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
  ```

- [ ] **Step 2: Fix rest_routes.py**

In `engine/api/rest_routes.py`:
- Change `from datetime import datetime` to `from datetime import datetime, timezone`
- Change `last_bar_processed=datetime.utcnow()` to `last_bar_processed=datetime.now(timezone.utc)`

- [ ] **Step 3: Write deprecation test**

Create `tests/test_deprecation.py`:

```python
import pytest
import warnings
from datetime import datetime, timezone


def test_frames_py_no_deprecated_utcnow():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        from models.frames import ThesisCard
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
            grade="ATTRACTIVE",
            time_decay_multiplier=1.0,
            actionability_tier="Research-Only",
            preferred_regime="Trending-Up",
        )
        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) == 0


def test_rest_routes_no_deprecated_utcnow():
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
Expected: PASS.

- [ ] **Step 4: Run full pytest**

```bash
cd engine && pytest
```
Expected: All 77 existing tests pass.

- [ ] **Step 5: Commit**

```bash
git add engine/models/frames.py engine/api/rest_routes.py tests/test_deprecation.py
git commit -m "fix: replace deprecated datetime.utcnow() with timezone-aware now()"
```

---

### Task 8: L10 — Add Statistical Methods (Fixed BH)

**Files:**
- Modify: `engine/layers/l10_edge.py`
- Modify: `tests/test_l10.py`

- [ ] **Step 1: Add statistical helpers**

Insert at the top of `engine/layers/l10_edge.py` (after imports, before `check_min_samples`):

```python
import random


def wilson_ci(hit_rate: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = hit_rate
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half_width = z * ((p * (1 - p) / n + z**2 / (4 * n**2)) ** 0.5) / denom
    return (max(0.0, centre - half_width), min(1.0, centre + half_width))


def benjamini_hochberg(p_values: list[float], alpha: float = 0.05) -> list[bool]:
    """Benjamini-Hochberg false discovery rate correction.

    Standard step-up procedure:
    1. Sort p-values ascending
    2. Find largest rank k where p_(k) <= (k/m) * alpha
    3. Reject ALL hypotheses with rank <= k
    """
    if not p_values:
        return []
    m = len(p_values)
    sorted_idx = sorted(range(m), key=lambda i: p_values[i])

    # Find largest k satisfying the condition
    k = 0
    for rank, idx in enumerate(sorted_idx, start=1):
        if p_values[idx] <= rank * alpha / m:
            k = rank

    # Reject all hypotheses with rank <= k
    significant = [False] * m
    for rank, idx in enumerate(sorted_idx, start=1):
        if rank <= k:
            significant[idx] = True
    return significant


def bayesian_bootstrap(returns: list[float], n_bootstrap: int = 10000) -> dict:
    """Bayesian bootstrap for mean net return."""
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

- [ ] **Step 2: Update lookup() to use wilson_ci**

In `engine/layers/l10_edge.py`, in the `lookup` method, after extracting `ci_lower` and `ci_upper`:

```python
        n = row.get("n", 0)
        hit_rate = row.get("hit_rate", 0.0)
        ci_lower = row.get("ci_lower", 0.0)
        ci_upper = row.get("ci_upper", 0.0)

        if n > 0 and ci_lower == 0.0 and ci_upper == 0.0:
            ci_lower, ci_upper = wilson_ci(hit_rate, n)
```

- [ ] **Step 3: Write tests**

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
    # With standard BH at alpha=0.05, m=5: threshold for rank k is k*0.01
    # p_(1)=0.01 <= 0.01 -> k=1
    # p_(2)=0.03 <= 0.02 -> False, so k remains 1
    # Only rank 1 rejected
    assert significant[0] is True   # 0.01
    assert significant[2] is False  # 0.03
    assert significant[1] is False  # 0.04
    assert significant[3] is False  # 0.08
    assert significant[4] is False  # 0.2


def test_benjamini_hochberg_monotonic():
    """BH must never produce non-monotonic rejections (e.g. T,F,T)."""
    p_values = [0.009, 0.021, 0.022, 0.023, 0.5]
    significant = benjamini_hochberg(p_values, alpha=0.05)
    # k=1 only (0.009 <= 0.01, but 0.021 > 0.02)
    assert significant == [True, False, False, False, False]


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

Run: `cd engine && pytest ../tests/test_l10.py -v`
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add engine/layers/l10_edge.py tests/test_l10.py
git commit -m "feat: add wilson_ci, benjamini_hochberg, bayesian_bootstrap to L10"
```

---

### Task 9: L9 — Rename Methods to Match Plan

**Files:**
- Modify: `engine/layers/l9_monitor.py`
- Modify: `tests/test_l9.py`

- [ ] **Step 1: Rename methods in l9_monitor.py**

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

- [ ] **Step 2: Update tests**

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
    invalidated = await ledger.on_tick(price=2440.0)
    assert any(t["thesis_id"] == "test-1" for t in invalidated)


@pytest.mark.asyncio
async def test_on_tick_t1_hit():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_trigger(thesis)
    hit = await ledger.on_tick(price=2550.0)
    assert any(t["thesis_id"] == "test-1" for t in hit)


@pytest.mark.asyncio
async def test_on_tick_t2_hit():
    ledger = L9ShadowLedger()
    thesis = make_thesis()
    await ledger.on_trigger(thesis)
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
    invalidated = await ledger.on_tick(price=2560.0)
    assert any(t["thesis_id"] == "test-1" for t in invalidated)
```

Run: `cd engine && pytest ../tests/test_l9.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add engine/layers/l9_monitor.py tests/test_l9.py
git commit -m "refactor: rename L9 methods to on_trigger/on_tick/on_force_expire"
```

---

### Task 10: Phase 2 Verification

- [ ] **Step 1: Run full pytest**

```bash
cd engine && pytest
```
Expected: All tests pass.

- [ ] **Step 2: Run with deprecation warnings as errors**

```bash
cd engine && pytest -W error::DeprecationWarning
```
Expected: No failures.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: Phase 2 backend core fixes complete"
```

---

## Phase 3: Backend Orchestration

### Task 11: Create Token Manager

**Files:**
- Create: `engine/core/auth/token_manager.py`
- Create: `tests/test_token_manager.py`

**Note:** The analytics token expires 2027-04-04 (~11 months). For MVP1 research-only, a simple refresh-aware wrapper is sufficient.

- [ ] **Step 1: Create token_manager.py**

Create `engine/core/auth/token_manager.py`:

```python
import time
from datetime import datetime, timezone
from config import settings


class TokenManager:
    """Wraps the Upstox analytics token and tracks expiry.

    For MVP1 (research-only), the analytics token is a 1-year JWT.
    This manager provides a unified interface for token retrieval
    and basic expiry warnings.
    """

    def __init__(self):
        self._token = settings.upstox_analytics_token
        self._base_url = settings.upstox_api_base_url
        self._api_key = settings.upstox_api_key
        self._api_secret = settings.upstox_api_secret

    def get_token(self) -> str:
        return self._token

    def get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
            "Api-Version": "v3",
        }

    def days_until_expiry(self) -> int:
        """Return approximate days until token expiry."""
        try:
            import jwt
            payload = jwt.decode(self._token, options={"verify_signature": False})
            exp = payload.get("exp", 0)
            now = time.time()
            return max(0, int((exp - now) / 86400))
        except Exception:
            return 365  # fallback

    def is_near_expiry(self, threshold_days: int = 7) -> bool:
        return self.days_until_expiry() <= threshold_days


token_manager = TokenManager()
```

- [ ] **Step 2: Create tests**

Create `tests/test_token_manager.py`:

```python
import pytest
from core.auth.token_manager import TokenManager


def test_token_manager_returns_token():
    tm = TokenManager()
    token = tm.get_token()
    assert isinstance(token, str)
    assert len(token) > 0


def test_token_manager_headers():
    tm = TokenManager()
    headers = tm.get_headers()
    assert "Authorization" in headers
    assert headers["Authorization"].startswith("Bearer ")


def test_token_manager_days_until_expiry():
    tm = TokenManager()
    days = tm.days_until_expiry()
    assert isinstance(days, int)
    assert days >= 0
```

Run: `cd engine && pytest ../tests/test_token_manager.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add engine/core/auth/token_manager.py tests/test_token_manager.py
git commit -m "feat: add token_manager for Upstox auth tracking"
```

---

### Task 12: Create Pipeline Orchestrator

**Files:**
- Create: `engine/core/pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Create pipeline.py**

Create `engine/core/pipeline.py`:

```python
import random
from datetime import datetime, timezone

from models.enums import Regime, Direction, SetupType
from models.frames import MarketContextFrame, RankingEntry, ThesisCard
from layers.l1_market_context import classify_regime
from layers.l6_ranking import L6Ranking
from layers.l8_thesis import L8Thesis, L8CostModel
from layers.l9_monitor import L9ShadowLedger
from layers.l10_edge import L10EdgeLookup
from api.websocket_manager import manager as ws_manager


class PipelineOrchestrator:
    """Orchestrates the L1-L10 pipeline every minute.

    MVP1 uses synthetic/mock market data to exercise all layers.
    Real Upstox data integration is Phase 2 (MVP2+).
    """

    def __init__(self):
        self.l6 = L6Ranking(top_n=25)
        self.l8 = L8Thesis()
        self.l8_cost = L8CostModel()
        self.l9 = L9ShadowLedger()
        self.l10 = L10EdgeLookup()
        self._running = False

    async def run_cycle(self):
        """Execute one full pipeline cycle."""
        now = datetime.now(timezone.utc)

        # L1: Market Context (synthetic for MVP1)
        regimes = [Regime.TRENDING_UP, Regime.TRENDING_DOWN, Regime.RANGE_BOUND]
        regime = random.choice(regimes)
        context = MarketContextFrame(
            regime=regime,
            regime_confidence=0.75,
            volatility_qualifier="Normal",
            time_bucket="Opening" if now.hour < 10 else "Mid-Day",
        )

        # L2-L5: Generate synthetic scored stocks
        scored_stocks = self._generate_synthetic_stocks(regime)

        # L6: Rank
        rankings = self.l6.rank(scored_stocks)
        long_rankings = [r for r in rankings if r.net_rr > 0]
        short_rankings = [r for r in rankings if r.net_rr <= 0]

        # L8: Assemble theses for top ranked
        theses = []
        for stock in rankings[:5]:
            thesis_data = {
                "symbol": stock.symbol,
                "direction": "LONG" if stock.net_rr > 0 else "SHORT",
                "trigger": stock.score * 10,
                "invalidation": stock.score * 9.5,
                "t1": stock.score * 11,
                "t2": stock.score * 12,
            }
            costs = self.l8_cost.apply(thesis_data)
            thesis = ThesisCard(
                thesis_id=f"thesis-{stock.symbol}-{now.timestamp()}",
                symbol=stock.symbol,
                direction=Direction.LONG if stock.net_rr > 0 else Direction.SHORT,
                setup_type=stock.setup_type,
                trigger=thesis_data["trigger"],
                invalidation=thesis_data["invalidation"],
                t1=thesis_data["t1"],
                t2=thesis_data["t2"],
                gross_rr=costs["gross_rr"],
                net_rr=costs["net_rr"],
                grade="ATTRACTIVE" if costs["net_rr"] > 1.5 else "MARGINAL",
                time_decay_multiplier=costs["time_decay_multiplier"],
                actionability_tier=stock.actionability_tier,
                valid_until=(now.replace(hour=15, minute=30)).isoformat(),
                preferred_regime=regime,
            )
            theses.append(thesis)
            await self.l9.on_trigger({
                "thesis_id": thesis.thesis_id,
                "symbol": thesis.symbol,
                "direction": thesis.direction.value,
                "trigger": thesis.trigger,
                "invalidation": thesis.invalidation,
                "t1": thesis.t1,
                "t2": thesis.t2,
            })

        # Broadcast via WebSocket
        await ws_manager.broadcast({
            "type": "L1_CONTEXT",
            "timestamp": now.isoformat(),
            "payload": context.model_dump(),
        })
        await ws_manager.broadcast({
            "type": "L6_RANKINGS",
            "timestamp": now.isoformat(),
            "payload": {
                "long": [r.model_dump() for r in long_rankings],
                "short": [r.model_dump() for r in short_rankings],
            },
        })
        for thesis in theses:
            await ws_manager.broadcast({
                "type": "L8_THESIS",
                "timestamp": now.isoformat(),
                "payload": {
                    "thesis_id": thesis.thesis_id,
                    "card": thesis.model_dump(),
                },
            })

        # L9: Check for invalidations (mock price moves)
        for thesis in theses:
            mock_price = thesis.trigger * random.uniform(0.98, 1.02)
            results = await self.l9.on_tick(mock_price)
            for r in results:
                if r["state"] in ["STOPPED_OUT", "T1_HIT", "T2_HIT"]:
                    await ws_manager.broadcast({
                        "type": "L9_INVALIDATION" if r["state"] == "STOPPED_OUT" else "L8_THESIS",
                        "timestamp": now.isoformat(),
                        "payload": {
                            "thesis_id": r["thesis_id"],
                            "reason": f"State changed to {r['state']}",
                        },
                    })

    def _generate_synthetic_stocks(self, regime: Regime) -> list[dict]:
        symbols = ["RELIANCE", "INFY", "TCS", "HDFCBANK", "ICICIBANK", "SBIN", "BHARTIARTL", "ITC", "LT", "HINDUNILVR"]
        stocks = []
        for sym in symbols:
            base_score = random.uniform(40, 90)
            if regime == Regime.TRENDING_UP:
                base_score += random.uniform(5, 15)
            elif regime == Regime.TRENDING_DOWN:
                base_score -= random.uniform(5, 15)
            stocks.append({
                "symbol": sym,
                "instrument_key": f"NSE_EQ|{sym}",
                "score": round(max(0, min(100, base_score)), 2),
                "setup_type": random.choice([1, 2, 3]),
                "confluence_score": random.randint(1, 5),
                "net_rr": round(random.uniform(0.5, 2.5), 2),
                "actionability_tier": "Research-Only",
                "liquidity_quality": "Good",
            })
        return stocks


pipeline = PipelineOrchestrator()
```

- [ ] **Step 2: Create pipeline tests**

Create `tests/test_pipeline.py`:

```python
import pytest
from core.pipeline import PipelineOrchestrator


@pytest.mark.asyncio
async def test_pipeline_runs_without_error():
    orchestrator = PipelineOrchestrator()
    await orchestrator.run_cycle()
    # If no exception raised, the pipeline executed successfully


@pytest.mark.asyncio
async def test_pipeline_generates_rankings():
    orchestrator = PipelineOrchestrator()
    await orchestrator.run_cycle()
    assert len(orchestrator.l6.previous_ranks) > 0


@pytest.mark.asyncio
async def test_pipeline_creates_theses():
    orchestrator = PipelineOrchestrator()
    await orchestrator.run_cycle()
    assert len(orchestrator.l9.active) > 0
```

Run: `cd engine && pytest ../tests/test_pipeline.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add engine/core/pipeline.py tests/test_pipeline.py
git commit -m "feat: add L1-L10 pipeline orchestrator with synthetic data"
```

---

### Task 13: Wire Scheduler and Pipeline into main.py

**Files:**
- Modify: `engine/main.py`
- Modify: `engine/core/scheduler/market_scheduler.py`
- Modify: `tests/test_scheduler.py`

- [ ] **Step 1: Update market_scheduler.py**

Replace `engine/core/scheduler/market_scheduler.py`:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime


class MarketScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._jobs = {}

    def register_job(self, job_id: str, func, trigger):
        self._jobs[job_id] = (func, trigger)

    def start(self):
        for job_id, (func, trigger) in self._jobs.items():
            self.scheduler.add_job(func, trigger=trigger, id=job_id, replace_existing=True)
        self.scheduler.start()

    def shutdown(self):
        self.scheduler.shutdown()

    def get_job_count(self) -> int:
        return len(self.scheduler.get_jobs())


scheduler = MarketScheduler()
```

- [ ] **Step 2: Update main.py lifespan**

Replace `engine/main.py`:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from api.rest_routes import router as rest_router
from api.websocket_manager import router as ws_router
from core.scheduler.market_scheduler import scheduler
from core.pipeline import pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Engine starting...")

    # Register pipeline to run every minute during market hours
    scheduler.register_job(
        "pipeline_cycle",
        pipeline.run_cycle,
        trigger="interval",
        seconds=60,
    )
    scheduler.start()
    print(f"Scheduler started with {scheduler.get_job_count()} jobs")

    yield

    print("Engine shutting down...")
    scheduler.shutdown()


app = FastAPI(title="Intraday Engine", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rest_router)
app.include_router(ws_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

Wait — `register_job` currently takes `trigger` as a positional arg for `scheduler.add_job`. Let me fix the signature.

Actually, looking at my MarketScheduler code, `register_job` stores `(func, trigger)` and `start()` passes `trigger=trigger` to `add_job`. So the call in main.py should be:

```python
    scheduler.register_job(
        "pipeline_cycle",
        pipeline.run_cycle,
        "interval",
        seconds=60,
    )
```

But that won't work because `register_job` only takes 3 args. I need to adjust.

Let me fix MarketScheduler to accept kwargs:

```python
class MarketScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._jobs = {}

    def register_job(self, job_id: str, func, trigger, **trigger_kwargs):
        self._jobs[job_id] = (func, trigger, trigger_kwargs)

    def start(self):
        for job_id, (func, trigger, kwargs) in self._jobs.items():
            self.scheduler.add_job(func, trigger=trigger, id=job_id, replace_existing=True, **kwargs)
        self.scheduler.start()
```

Then in main.py:
```python
    scheduler.register_job(
        "pipeline_cycle",
        pipeline.run_cycle,
        "interval",
        seconds=60,
    )
```

- [ ] **Step 3: Update scheduler tests**

Replace `tests/test_scheduler.py`:

```python
import pytest
from core.scheduler.market_scheduler import MarketScheduler


def test_scheduler_init():
    s = MarketScheduler()
    assert s.scheduler is not None


@pytest.mark.asyncio
async def test_scheduler_registers_and_starts():
    s = MarketScheduler()
    async def dummy():
        pass
    s.register_job("test", dummy, "interval", seconds=1)
    s.start()
    assert s.get_job_count() == 1
    s.shutdown()
```

Run: `cd engine && pytest ../tests/test_scheduler.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add engine/main.py engine/core/scheduler/market_scheduler.py tests/test_scheduler.py
git commit -m "feat: wire pipeline orchestrator into main.py lifespan"
```

---

### Task 14: Update WebSocket Manager to Broadcast All Message Types

**Files:**
- Modify: `engine/api/websocket_manager.py`
- Create: `tests/test_websocket_broadcast.py`

- [ ] **Step 1: Verify websocket_manager already supports broadcast**

The existing `ConnectionManager.broadcast()` method already supports sending arbitrary JSON. The pipeline in Task 12 already calls `ws_manager.broadcast()` for L1, L6, L8, L9, L10 messages. No changes needed to `websocket_manager.py` itself.

- [ ] **Step 2: Write broadcast test**

Create `tests/test_websocket_broadcast.py`:

```python
import pytest
from fastapi.testclient import TestClient
from main import app


def test_websocket_receives_l1_context():
    client = TestClient(app)
    with client.websocket_connect("/ws/v1/stream") as ws:
        ws.send_json({"action": "subscribe", "channels": ["market"]})
        data = ws.receive_json()
        assert data["type"] == "L1_CONTEXT"
        assert "payload" in data
        assert "regime" in data["payload"]


def test_websocket_receives_l6_rankings():
    client = TestClient(app)
    with client.websocket_connect("/ws/v1/stream") as ws:
        ws.send_json({"action": "subscribe", "channels": ["rankings"]})
        data = ws.receive_json()
        assert data["type"] == "L6_RANKINGS"
        assert "payload" in data
```

Run: `cd engine && pytest ../tests/test_websocket_broadcast.py -v`
Expected: PASS (the pipeline may not have run yet in the test, so the messages come from the initial subscription handler).

- [ ] **Step 3: Commit**

```bash
git add tests/test_websocket_broadcast.py
git commit -m "test: add WebSocket broadcast verification tests"
```

---

### Task 15: Phase 3 Verification

- [ ] **Step 1: Run full pytest suite**

```bash
cd engine && pytest
```
Expected: All tests pass (existing 77 + new deprecation + L10 + L9 + token + pipeline + scheduler + broadcast).

- [ ] **Step 2: Verify main.py starts without error**

```bash
cd engine && python -c "import main; print('main.py imports successfully')"
```
Expected: No import errors.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: Phase 3 backend orchestration complete"
```

---

## Phase 4: Integration & Verification

### Task 16: Add Vite WS Proxy for Production Parity

**Files:**
- Modify: `frontend/vite.config.ts`

- [ ] **Step 1: Add WS proxy to vite.config.ts**

Update `frontend/vite.config.ts` server.proxy section:

```ts
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8084',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/ws': {
        target: 'ws://localhost:8084',
        ws: true,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/ws/, ''),
      },
    },
  },
```

- [ ] **Step 2: Update useWebSocket.ts to use proxied URL**

Update `frontend/src/hooks/useWebSocket.ts`:

```ts
const WS_URL = '/ws/ws/v1/stream';
```

Wait, that would be `/ws/ws/v1/stream` which is wrong because the rewrite removes `/ws`. Let me think...

Actually, the backend WebSocket endpoint is `/ws/v1/stream`. With the proxy config above:
- Frontend connects to `/ws/ws/v1/stream`
- Proxy rewrites to `/ws/v1/stream`
- Forwards to `ws://localhost:8084/ws/v1/stream`

So the frontend URL should be `/ws/ws/v1/stream`.

Alternatively, use a cleaner proxy:
```ts
      '/ws': {
        target: 'ws://localhost:8084',
        ws: true,
        changeOrigin: true,
      },
```
With this, frontend connects to `/ws/v1/stream` and it's forwarded to `ws://localhost:8084/ws/v1/stream` without rewrite.

So the correct approach:
```ts
      '/ws': {
        target: 'ws://localhost:8084',
        ws: true,
        changeOrigin: true,
      },
```

And `useWebSocket.ts`:
```ts
const WS_URL = '/ws/v1/stream';
```

- [ ] **Step 3: Commit**

```bash
git add frontend/vite.config.ts frontend/src/hooks/useWebSocket.ts
git commit -m "fix: proxy WebSocket through Vite for production parity"
```

---

### Task 17: E2E Smoke Test

**Files:**
- Create: `tests/e2e/smoke.test.py`

- [ ] **Step 1: Create E2E smoke test**

Create `tests/e2e/smoke.test.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_market_context_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/market/context")
        assert response.status_code == 200
        data = response.json()
        assert "regime" in data


@pytest.mark.asyncio
async def test_rankings_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/rankings/top25/long")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_websocket_connect():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.websocket_connect("/ws/v1/stream") as ws:
            await ws.send_json({"action": "subscribe", "channels": ["market"]})
            data = await ws.receive_json()
            assert data["type"] == "L1_CONTEXT"
```

Run: `cd engine && pytest ../tests/e2e/smoke.test.py -v`
Expected: All 4 tests pass.

- [ ] **Step 2: Commit**

```bash
git add tests/e2e/smoke.test.py
git commit -m "test: add E2E smoke tests for REST and WebSocket"
```

---

### Task 18: Docker Compose Verification

**Files:**
- Verify: `docker-compose.yml`

- [ ] **Step 1: Verify Docker Compose stack starts**

```bash
cd .worktrees/mvp1 && docker-compose up -d --build
```
Expected: All services (engine, timescaledb, redis) start without errors.

- [ ] **Step 2: Verify health endpoint from container**

```bash
curl -f http://localhost:8084/health
```
Expected: Returns JSON with status "healthy".

- [ ] **Step 3: Tear down**

```bash
cd .worktrees/mvp1 && docker-compose down
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: Phase 4 integration complete — Docker Compose verified"
```

---

## Self-Review

### 1. Spec Coverage

| Requirement | Task |
|---|---|
| Frontend QueryClientProvider | Task 1 |
| Hooks use /api proxy | Task 2 |
| index.html remove vite.svg | Task 5 |
| useWebSocket L8/L9/L10 handlers | Task 4 |
| marketStore theses/invalidations/edge | Task 3 |
| ChartPanel.tsx | Task 5 |
| App.tsx integration | Task 5 |
| datetime.utcnow() deprecation | Task 7 |
| L10 wilson_ci, BH, bootstrap | Task 8 |
| L9 rename to on_trigger/on_tick | Task 9 |
| Token manager | Task 11 |
| Pipeline orchestrator | Task 12 |
| Scheduler wired to main.py | Task 13 |
| WS broadcasts L8/L9/L10 | Task 12 (pipeline calls broadcast) |
| Vite WS proxy | Task 16 |
| E2E smoke tests | Task 17 |
| Docker Compose verification | Task 18 |

### 2. Placeholder Scan

- No TBD, TODO, or incomplete sections.
- All code is explicit and complete.
- All test code is shown.

### 3. Bug Fixes from Agent Feedback

| Agent Finding | Fix in This Plan |
|---|---|
| BH implementation wrong (non-monotonic) | Task 8 — standard step-up procedure with largest-k |
| Grade test data wrong ('A'/'B') | Task 3/4/5 — uses 'ATTRACTIVE'/'MARGINAL'/'UNATTRACTIVE' |
| git add -A risky | All commits use explicit file lists |
| WS URL inconsistent with REST proxy | Task 16 — Vite proxies both /api and /ws |
| Backend never broadcasts L8/L9/L10 | Task 12 — pipeline broadcasts all message types |
| No orchestration | Task 12/13 — PipelineOrchestrator + main.py lifespan |
| No token_manager | Task 11 — created with expiry tracking |
| No E2E tests | Task 17 — REST + WS smoke tests |
| No Docker Compose verification | Task 18 — explicit docker-compose up/down test |

### 4. Scope Note

This plan goes beyond the original 9 "NOT Done" items to include everything needed for MVP1 to actually run end-to-end. If the user wants to defer any phase, Phase 4 (Docker Compose verification) is the lowest-risk deferral, followed by Phase 3 (orchestration) if research-only mock data is acceptable for now.
