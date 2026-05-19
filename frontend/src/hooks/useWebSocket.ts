import { useEffect, useRef } from 'react';
import { useMarketStore } from '@/stores/marketStore';
import type { WSMessage } from '@/types/api';

const WS_URL = '/ws/v1/stream';

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null);
  const setWsConnected = useMarketStore((s) => s.setWsConnected);
  const setContext = useMarketStore((s) => s.setContext);
  const setRankings = useMarketStore((s) => s.setRankings);
  const addOrUpdateThesis = useMarketStore((s) => s.addOrUpdateThesis);
  const invalidateThesis = useMarketStore((s) => s.invalidateThesis);
  const updateEdgeTier = useMarketStore((s) => s.updateEdgeTier);
  const setWSTimestamp = useMarketStore((s) => s.setWSTimestamp);
  const setSource = useMarketStore((s) => s.setSource);

  useEffect(() => {
    const socket = new WebSocket(WS_URL);
    ws.current = socket;

    socket.onopen = () => {
      setWsConnected(true);
      socket.send(JSON.stringify({ action: 'subscribe', channels: ['market', 'rankings', 'theses', 'edge'] }));
    };

    socket.onmessage = (event) => {
      const msg: WSMessage = JSON.parse(event.data);
      setWSTimestamp(msg.type, msg.timestamp);
      const wsSource = msg.source ?? 'unknown';
      const key = `ws/${msg.type.toLowerCase()}`;
      setSource(key, wsSource);
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

    return () => { socket.close(); };
  }, [setWsConnected, setContext, setRankings, addOrUpdateThesis, invalidateThesis, updateEdgeTier, setWSTimestamp, setSource]);
}
